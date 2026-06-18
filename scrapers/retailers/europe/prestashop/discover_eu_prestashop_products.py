from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlencode

import requests


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.europe.common.discovery_utils import (  # noqa: E402
    dedupe_rows,
    decorate_rows,
    product_rows_from_json_ld,
    product_rows_from_links,
    product_rows_from_prestashop_cards,
    product_rows_from_prestashop_json,
    strip_tags,
)
from scrapers.retailers.europe.common.fetch_utils import fetch_text  # noqa: E402


INPUT_FILE = Path("scrapers/retailers/europe/prestashop/eu_prestashop_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/europe/prestashop/output/eu_prestashop_product_discovery.json")


def page_url(url: str, page: int) -> str:
    if page <= 1:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode({'page': page})}"


def enrich_available_sizes(row: dict) -> list[dict]:
    try:
        response = requests.get(
            row.get("productUrl", ""),
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0 QuivrrEUPrestaDiscovery/1.0"},
        )
        response.raise_for_status()
    except requests.RequestException as error:
        return [{**row, "detailFetchStatus": f"{type(error).__name__}: {error}"}]

    html = response.text
    available_sizes = []
    for match in re.finditer(
        r'<li\b[^>]*class=["\']([^"\']*)["\'][^>]*>\s*<input[^>]*data-product-attribute=["\']11["\'][^>]*title=["\']([^"\']+)["\']',
        html,
        re.I | re.S,
    ):
        classes, title = match.groups()
        if "attribute-not-in-stock" in classes.lower():
            continue
        size = strip_tags(unescape(title)).replace("''", "").replace('"', "")
        if size and size not in available_sizes:
            available_sizes.append(size)

    if not available_sizes:
        page_rows = product_rows_from_json_ld(html, row.get("productUrl", ""))
        detail = page_rows[0] if page_rows else {}
        return [{
            **row,
            "isAvailable": detail.get("isAvailable", row.get("isAvailable")),
            "stockStatus": detail.get("stockStatus") or row.get("stockStatus"),
            "sourceSnippet": f"{row.get('sourceSnippet', '')} {strip_tags(html)[:10000]}",
        }]

    return [{
        **row,
        "productTitle": f"{row.get('productTitle')} - {size}",
        "isAvailable": True,
        "stockStatus": "in_stock",
        "sourceSnippet": f"{row.get('sourceSnippet', '')} {size}",
    } for size in available_sizes]


def discover_target(target: dict, max_pages: int) -> dict:
    products = []
    rejected = 0
    fetches = []

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

            rows = product_rows_from_prestashop_json(response.text, source_url)
            rows.extend(product_rows_from_prestashop_cards(response.text, source_url))
            rows.extend(product_rows_from_json_ld(response.text, source_url))
            rows.extend(product_rows_from_links(response.text, source_url, ["/en/", "/product", ".html"]))
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
    product_url_regex = target.get("productUrlRegex")
    if product_url_regex:
        unique_products = [
            row for row in unique_products
            if re.search(product_url_regex, row.get("productUrl", ""), re.I)
        ]
    if target.get("expandAvailableSizes"):
        with ThreadPoolExecutor(max_workers=40) as executor:
            groups = list(executor.map(enrich_available_sizes, unique_products))
        expanded = {}
        for row in [item for group in groups for item in group]:
            key = (
                str(row.get("productUrl") or "").lower(),
                str(row.get("productTitle") or "").lower(),
            )
            expanded.setdefault(key, row)
        unique_products = list(expanded.values())

    return {
        "target": target["retailerSlug"],
        "pagesCrawled": sum(1 for fetch in fetches if fetch["status"] == "ok"),
        "rawCategoryRows": len(products),
        "uniqueCanonicalProducts": len(unique_products),
        "paginationMethod": "PrestaShop ?page={page} until empty or duplicate page",
        "productsAccepted": len(unique_products),
        "productsRejected": rejected,
        "fetches": fetches,
        "products": unique_products,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover EU PrestaShop surfboard products without SQL writes.")
    parser.add_argument("--run-enabled", action="store_true", help="Fetch enabled targets. Without this, no network calls run.")
    parser.add_argument("--target", default="", help="Optional retailerSlug filter.")
    parser.add_argument("--max-pages", type=int, default=1, help="Maximum category pages per target.")
    parser.add_argument(
        "--enrich-existing",
        action="store_true",
        help="Reuse the saved exhaustive listing and rerun detail enrichment only.",
    )
    args = parser.parse_args()

    targets = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    selected = [target for target in targets if args.run_enabled and target.get("enabled") is True]
    if args.target:
        selected = [target for target in selected if target.get("retailerSlug") == args.target]

    if args.enrich_existing:
        existing = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        saved_products = existing.get("products", [])
        results = []
        for target in selected:
            rows = [row for row in saved_products if row.get("retailerSlug") == target["retailerSlug"]]
            if target.get("expandAvailableSizes"):
                with ThreadPoolExecutor(max_workers=40) as executor:
                    groups = list(executor.map(enrich_available_sizes, rows))
                rows = [item for group in groups for item in group]
            prior = next(
                (result for result in existing.get("results", []) if result.get("target") == target["retailerSlug"]),
                {},
            )
            results.append({
                **prior,
                "target": target["retailerSlug"],
                "uniqueCanonicalProducts": len(rows),
                "productsAccepted": len(rows),
                "products": rows,
            })
    else:
        results = [discover_target(target, max(0, args.max_pages)) for target in selected]
    products = [product for result in results for product in result["products"]]
    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "run_enabled" if args.run_enabled else "dry_run",
        "purpose": "EU PrestaShop product discovery only. No SQL import or production table writes.",
        "targetsConfigured": len(targets),
        "targetsSelected": len(selected),
        "results": [{key: value for key, value in result.items() if key != "products"} for result in results],
        "products": products,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"EU PrestaShop discovery: {report['mode']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
