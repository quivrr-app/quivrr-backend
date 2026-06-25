from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.europe.common.discovery_utils import (  # noqa: E402
    classify_product,
    clean,
    dedupe_rows,
    decorate_rows,
    product_rows_from_json_ld,
    product_rows_from_links,
    product_rows_from_woocommerce_cards,
    strip_tags,
)
from scrapers.retailers.europe.common.fetch_utils import fetch_text  # noqa: E402


INPUT_FILE = Path("scrapers/retailers/usa/woocommerce/us_woocommerce_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/usa/woocommerce/output/us_woocommerce_product_discovery.json")
STORE_API_PAGE_SIZE = 100
STORE_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 QuivrrProbe/1.0",
    "Accept": "application/json,text/plain,*/*",
}


def page_url(url: str, page: int) -> str:
    if page <= 1:
        return url
    return f"{url.rstrip('/')}/page/{page}/"


def variation_size(value: object) -> str:
    text_value = str(value or "").strip().lower()
    match = re.fullmatch(r"([4-9]|1[0-2])[-_']?(\d{1,2})", text_value)
    return f"{match.group(1)}'{int(match.group(2))}" if match else text_value


def enrich_product_variants(row: dict) -> list[dict]:
    response = fetch_text(row.get("productUrl", ""), retries=0)
    if not response.ok:
        return [{**row, "detailFetchStatus": response.status}]

    html = response.text
    match = re.search(r'data-product_variations=["\'](.*?)["\']', html, re.I | re.S)
    page_text = strip_tags(html)[:30000]
    if not match:
        return [{**row, "sourceSnippet": f"{row.get('sourceSnippet', '')} {page_text}"}]

    try:
        variations = json.loads(unescape(match.group(1)))
    except (json.JSONDecodeError, TypeError):
        return [{**row, "sourceSnippet": f"{row.get('sourceSnippet', '')} {page_text}"}]
    if not isinstance(variations, list):
        return [{**row, "sourceSnippet": f"{row.get('sourceSnippet', '')} {page_text}"}]

    expanded = []
    for variation in variations:
        attributes = variation.get("attributes") or {}
        attribute_values = [variation_size(value) for value in attributes.values() if value]
        title_suffix = " - ".join(value for value in attribute_values if value)
        availability = unescape(str(variation.get("availability_html") or ""))
        is_available = "in-stock" in availability or bool(variation.get("is_in_stock"))
        image = variation.get("image") if isinstance(variation.get("image"), dict) else {}
        expanded.append({
            **row,
            "productTitle": f"{row.get('productTitle')} - {title_suffix}" if title_suffix else row.get("productTitle"),
            "productImageUrl": image.get("src") or row.get("productImageUrl"),
            "priceAmount": variation.get("display_price") or row.get("priceAmount"),
            "isAvailable": is_available,
            "stockStatus": "in_stock" if is_available else "out_of_stock",
            "sku": variation.get("sku") or row.get("sku"),
            "sourceSnippet": " ".join([
                row.get("sourceSnippet", ""),
                title_suffix,
                strip_tags(unescape(str(variation.get("variation_description") or ""))),
                page_text,
            ])[:40000],
        })
    return expanded or [{**row, "sourceSnippet": f"{row.get('sourceSnippet', '')} {page_text}"}]


def store_api_page_url(url: str, page: int) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}per_page={STORE_API_PAGE_SIZE}&page={page}"


def product_rows_from_store_api(items: list[dict], target: dict, source_url: str) -> tuple[list[dict], int]:
    rows = []
    rejected = 0

    for item in items:
        if not isinstance(item, dict):
            continue
        name = clean(item.get("name"))
        permalink = clean(item.get("permalink"))
        extra_text = " ".join(
            [
                name,
                strip_tags(unescape(str(item.get("short_description") or ""))),
                strip_tags(unescape(str(item.get("description") or ""))),
            ]
        )
        score = classify_product(name, permalink, extra_text)
        if not score["accepted"]:
            rejected += 1
            continue

        images = item.get("images") if isinstance(item.get("images"), list) else []
        image_url = ""
        if images and isinstance(images[0], dict):
            image_url = clean(images[0].get("src"))

        prices = item.get("prices") if isinstance(item.get("prices"), dict) else {}
        raw_price = prices.get("price")
        if isinstance(raw_price, str) and raw_price.isdigit():
            price_amount = f"{int(raw_price) / 100:.2f}"
        else:
            price_amount = clean(raw_price)

        rows.append(
            {
                "retailerSlug": target["retailerSlug"],
                "retailerName": target["retailerName"],
                "regionCode": target["regionCode"],
                "country": target["country"],
                "platform": target["platform"],
                "sourceUrl": source_url,
                "productTitle": name,
                "productUrl": permalink,
                "productImageUrl": image_url,
                "brand": "",
                "vendor": "",
                "priceAmount": price_amount,
                "priceCurrency": clean(prices.get("currency_code")) or target.get("priceCurrency", "USD"),
                "isAvailable": item.get("is_in_stock") if isinstance(item.get("is_in_stock"), bool) else None,
                "stockStatus": "in_stock" if item.get("is_in_stock") is True else "out_of_stock" if item.get("is_in_stock") is False else "",
                "sku": clean(item.get("sku")),
                "sourceSnippet": extra_text[:1000],
                "parseConfidence": score["parseConfidence"],
                "discoveryStatus": "accepted",
                "filterReasons": score["filterReasons"],
            }
        )

    return rows, rejected


def discover_target(target: dict, max_pages: int) -> dict:
    products = []
    rejected = 0
    fetches = []

    store_api_url = clean(target.get("storeApiUrl"))
    if store_api_url:
        page = 1
        while max_pages <= 0 or page <= max_pages:
            source_url = store_api_page_url(store_api_url, page)
            try:
                response = requests.get(source_url, headers=STORE_API_HEADERS, timeout=25)
                status = "ok" if response.status_code == 200 else "http_error"
                fetches.append({
                    "url": source_url,
                    "status": status,
                    "httpStatus": response.status_code,
                    "finalUrl": response.url,
                    "reason": "" if response.status_code == 200 else f"HTTP {response.status_code}",
                })
                if response.status_code != 200:
                    break
                items = response.json()
                if not isinstance(items, list) or not items:
                    break
                rows, rejected_count = product_rows_from_store_api(items, target, source_url)
                if not rows:
                    rejected += rejected_count
                    page += 1
                    continue
                products.extend(rows)
                rejected += rejected_count
                if len(items) < STORE_API_PAGE_SIZE:
                    break
                page += 1
            except Exception as error:
                fetches.append({
                    "url": source_url,
                    "status": "network_error",
                    "httpStatus": None,
                    "finalUrl": source_url,
                    "reason": f"{type(error).__name__}: {error}",
                })
                break

    for category_url in target.get("categoryUrls", []):
        page = 1
        seen_urls = set()
        while max_pages <= 0 or page <= max_pages:
            source_url = page_url(category_url, page)
            response = fetch_text(source_url)
            fetches.append({
                "url": source_url,
                "status": response.status,
                "httpStatus": response.http_status,
                "finalUrl": response.final_url,
                "reason": response.reason,
            })

            if not response.ok:
                break

            rows = product_rows_from_woocommerce_cards(response.text, source_url)
            rows.extend(product_rows_from_json_ld(response.text, source_url))
            rows.extend(product_rows_from_links(response.text, source_url, ["/product/"]))
            accepted, rejected_count = decorate_rows(rows, target, source_url)
            new_urls = {
                row.get("productUrl", "").split("#", 1)[0].rstrip("/").lower()
                for row in accepted
                if row.get("productUrl")
            } - seen_urls
            if not rows or not new_urls:
                break
            products.extend(accepted)
            rejected += rejected_count
            seen_urls.update(new_urls)
            page += 1

    unique_products = dedupe_rows(products)
    with ThreadPoolExecutor(max_workers=8) as executor:
        enriched_groups = list(executor.map(enrich_product_variants, unique_products))
    enriched_products = {}
    for row in [row for group in enriched_groups for row in group]:
        key = (
            str(row.get("productUrl") or "").lower().rstrip("/"),
            str(row.get("sku") or row.get("productTitle") or "").lower(),
        )
        enriched_products.setdefault(key, row)
    enriched_products = list(enriched_products.values())

    return {
        "target": target["retailerSlug"],
        "pagesCrawled": sum(1 for fetch in fetches if fetch["status"] == "ok"),
        "rawCategoryRows": len(products),
        "uniqueCanonicalProducts": len(unique_products),
        "paginationMethod": "WooCommerce /page/{page}/ until empty or duplicate page",
        "productsAccepted": len(enriched_products),
        "productsRejected": rejected,
        "fetches": fetches,
        "products": enriched_products,
    }


def load_targets() -> list[dict]:
    return json.loads(INPUT_FILE.read_text(encoding="utf-8"))


def selected_targets(targets: list[dict], run_enabled: bool, target_slug: str) -> list[dict]:
    if not run_enabled:
        return []
    selected = [target for target in targets if target.get("enabled") is True]
    if target_slug:
        selected = [target for target in selected if target.get("retailerSlug") == target_slug]
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover US WooCommerce surfboard products without SQL writes.")
    parser.add_argument("--run-enabled", action="store_true", help="Fetch enabled targets. Without this, no network calls run.")
    parser.add_argument("--target", default="", help="Optional retailerSlug filter.")
    parser.add_argument("--max-pages", type=int, default=1, help="Maximum category pages per target.")
    args = parser.parse_args()

    targets = load_targets()
    targets_to_run = selected_targets(targets, args.run_enabled, args.target)
    results = [discover_target(target, max(0, args.max_pages)) for target in targets_to_run]
    products = [product for result in results for product in result["products"]]

    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "run_enabled" if args.run_enabled else "dry_run",
        "purpose": "US WooCommerce product discovery only. No SQL import or production table writes.",
        "targetsConfigured": len(targets),
        "targetsSelected": len(targets_to_run),
        "results": [{key: value for key, value in result.items() if key != "products"} for result in results],
        "products": products,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"US WooCommerce discovery: {report['mode']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
