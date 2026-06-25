from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.europe.common.discovery_utils import (  # noqa: E402
    classify_product,
    clean,
    dedupe_rows,
    strip_tags,
)
from scrapers.retailers.europe.common.fetch_utils import fetch_text  # noqa: E402


INPUT_FILE = Path("scrapers/retailers/usa/bigcommerce/us_bigcommerce_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/usa/bigcommerce/output/us_bigcommerce_product_discovery.json")
REGION_CODE = "US"

TITLE_LINK_RE = re.compile(
    r"<(?:h\d|p|div)[^>]*class=[\"'][^\"']*\bcard-title\b[^\"']*[\"'][^>]*>\s*<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
    re.I | re.S,
)
IMAGE_RE = re.compile(r"<img[^>]+(?:src|data-src)=[\"']([^\"']+)[\"']", re.I)
PRICE_RE = re.compile(
    r"<(?:span|div)[^>]*class=[\"'][^\"']*\bprice(?:--withoutTax)?\b[^\"']*[\"'][^>]*>(.*?)</(?:span|div)>",
    re.I | re.S,
)
MONEY_RE = re.compile(r"\$\s*[0-9,]+(?:\.[0-9]{2})?")


def page_url(url: str, page: int) -> str:
    if page <= 1:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}page={page}"


def product_rows_from_bigcommerce_cards(html: str, source_url: str) -> list[dict]:
    rows = []

    for title_link in TITLE_LINK_RE.finditer(html):
        href = clean(title_link.group(1))
        title = strip_tags(title_link.group(2))
        product_url = urljoin(source_url, href)
        product_url_lower = product_url.lower()
        if not title or "cart.php" in product_url_lower or product_url_lower.endswith("#"):
            continue

        snippet_start = max(0, title_link.start() - 2500)
        snippet_end = min(len(html), title_link.end() + 2000)
        card = html[snippet_start:snippet_end]
        image_match = IMAGE_RE.search(card)
        price_match = PRICE_RE.search(card)
        card_text = strip_tags(card)
        sold_out = "sold out" in card_text.lower()
        price_text = strip_tags(price_match.group(1)) if price_match else ""
        if not price_text:
            money_match = MONEY_RE.search(card_text)
            price_text = money_match.group(0) if money_match else ""

        rows.append(
            {
                "productTitle": title,
                "productUrl": product_url,
                "productImageUrl": urljoin(source_url, clean(image_match.group(1)))
                if image_match
                else "",
                "brand": "",
                "vendor": "",
                "priceAmount": price_text,
                "isAvailable": False if sold_out else True,
                "stockStatus": "out_of_stock" if sold_out else "in_stock",
                "sku": "",
                "sourceSnippet": card_text[:1000],
                "sourceUrl": source_url,
            }
        )

    return dedupe_rows(rows)


def decorate_rows(rows: list[dict], target: dict, source_url: str) -> tuple[list[dict], int]:
    accepted = []
    rejected = 0

    for row in rows:
        score = classify_product(
            row.get("productTitle", ""),
            row.get("productUrl", ""),
            row.get("sourceSnippet", ""),
        )
        if not score["accepted"]:
            rejected += 1
            continue

        accepted.append(
            {
                "retailerSlug": target["retailerSlug"],
                "retailerName": target["retailerName"],
                "regionCode": target["regionCode"],
                "country": target["country"],
                "platform": target["platform"],
                "sourceUrl": source_url,
                "productTitle": clean(row.get("productTitle")),
                "productUrl": clean(row.get("productUrl")),
                "productImageUrl": clean(row.get("productImageUrl")),
                "brand": clean(row.get("brand")),
                "vendor": clean(row.get("vendor")),
                "priceAmount": clean(row.get("priceAmount")),
                "priceCurrency": target.get("priceCurrency", "USD"),
                "isAvailable": row.get("isAvailable"),
                "stockStatus": clean(row.get("stockStatus")),
                "sku": clean(row.get("sku")),
                "sourceSnippet": clean(row.get("sourceSnippet"))[:1000],
                "parseConfidence": score["parseConfidence"],
                "discoveryStatus": "accepted",
                "filterReasons": score["filterReasons"],
            }
        )

    return accepted, rejected


def discover_target(target: dict, max_pages: int) -> dict:
    if target.get("regionCode") != REGION_CODE:
        raise RuntimeError(
            f"US BigCommerce discovery requires RegionCode 'US', got {target.get('regionCode')!r}."
        )

    products = []
    rejected = 0
    fetches = []

    for category_url in target.get("categoryUrls", []):
        page = 1
        seen_urls = set()
        while max_pages <= 0 or page <= max_pages:
            source_url = page_url(category_url, page)
            response = fetch_text(source_url)
            fetches.append(
                {
                    "url": source_url,
                    "status": response.status,
                    "httpStatus": response.http_status,
                    "finalUrl": response.final_url,
                    "reason": response.reason,
                }
            )
            if not response.ok:
                break

            rows = product_rows_from_bigcommerce_cards(response.text, source_url)
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
    return {
        "target": target["retailerSlug"],
        "pagesCrawled": sum(1 for fetch in fetches if fetch["status"] == "ok"),
        "rawCategoryRows": len(products),
        "uniqueCanonicalProducts": len(unique_products),
        "paginationMethod": "BigCommerce ?page=N until empty or duplicate page",
        "productsAccepted": len(unique_products),
        "productsRejected": rejected,
        "fetches": fetches,
        "products": unique_products,
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
    parser = argparse.ArgumentParser(description="Discover US BigCommerce surfboard products without SQL writes.")
    parser.add_argument("--run-enabled", action="store_true", help="Fetch enabled targets. Without this, no network calls run.")
    parser.add_argument("--target", default="", help="Optional retailerSlug filter.")
    parser.add_argument("--max-pages", type=int, default=0, help="Maximum category pages per target. Default 0 fetches until exhausted.")
    args = parser.parse_args()

    targets = load_targets()
    targets_to_run = selected_targets(targets, args.run_enabled, args.target)
    results = [discover_target(target, max(0, args.max_pages)) for target in targets_to_run]
    products = [product for result in results for product in result["products"]]

    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "run_enabled" if args.run_enabled else "dry_run",
        "purpose": "US BigCommerce product discovery only. No SQL import or production table writes.",
        "targetsConfigured": len(targets),
        "targetsSelected": len(targets_to_run),
        "results": [{key: value for key, value in result.items() if key != "products"} for result in results],
        "products": products,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"US BigCommerce discovery: {report['mode']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
