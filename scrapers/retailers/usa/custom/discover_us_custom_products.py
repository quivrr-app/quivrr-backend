from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.europe.common.discovery_utils import (  # noqa: E402
    classify_product,
    clean,
    dedupe_rows,
)
from scrapers.retailers.usa.normalise_us_retailer_inventory import normalise_row  # noqa: E402


INPUT_FILE = Path("scrapers/retailers/usa/custom/us_custom_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/usa/custom/output/us_custom_product_discovery.json")
REGION_CODE = "US"
FETCH_ATTEMPTS = 3
TIMEOUT_SECONDS = 45

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36 QuivrrUSCustomDiscovery/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

PRODUCT_LINK_RE = re.compile(
    r'href="(https://www\.reddogsurfshop\.com/product-page/[^"#?]+)"',
    re.I,
)
JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>\s*(\{.*?\})\s*</script>',
    re.I | re.S,
)


def fetch_html(url: str) -> dict:
    errors = []
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
            if response.status_code == 200:
                return {
                    "ok": True,
                    "httpStatus": response.status_code,
                    "finalUrl": response.url,
                    "text": response.text,
                    "error": "",
                    "attempts": attempt,
                    "responseBytes": len(response.content),
                }
            errors.append(f"attempt {attempt}: HTTP {response.status_code}")
            if response.status_code not in {408, 429, 500, 502, 503, 504}:
                break
        except requests.RequestException as error:
            errors.append(f"attempt {attempt}: {type(error).__name__}: {error}")
        if attempt < FETCH_ATTEMPTS:
            time.sleep(attempt * 1.5)
    return {
        "ok": False,
        "httpStatus": None,
        "finalUrl": url,
        "text": "",
        "error": "; ".join(errors),
        "attempts": FETCH_ATTEMPTS,
        "responseBytes": 0,
    }


def parse_listing_handles(html: str) -> list[str]:
    return sorted(set(PRODUCT_LINK_RE.findall(html)))


def parse_product_json_ld(html: str, product_url: str, target: dict) -> dict | None:
    match = JSON_LD_RE.search(html)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if clean(data.get("@type")).lower() != "product":
        return None

    offers = data.get("Offers") or data.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}

    brand = data.get("brand") or {}
    if isinstance(brand, dict):
        brand_name = clean(brand.get("name"))
    else:
        brand_name = clean(brand)

    availability = clean(
        offers.get("Availability") or offers.get("availability")
    ).lower()
    is_available = True if "instock" in availability else False if "outofstock" in availability else None
    stock_status = "in_stock" if is_available is True else "out_of_stock" if is_available is False else ""

    images = data.get("image") or []
    image_url = ""
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict):
            image_url = clean(first.get("contentUrl") or first.get("url"))
        else:
            image_url = clean(first)
    elif isinstance(images, dict):
        image_url = clean(images.get("contentUrl") or images.get("url"))

    description = clean(data.get("description"))
    name = clean(data.get("name"))
    sku = clean(data.get("sku"))
    price = clean(offers.get("price"))

    soup = BeautifulSoup(html, "html.parser")
    og_description_tag = soup.find("meta", attrs={"property": "og:description"})
    og_description = clean(og_description_tag.get("content")) if og_description_tag else ""
    if og_description and og_description not in description:
        description = f"{description} {og_description}".strip()

    score = classify_product(
        f"{brand_name} {name}",
        product_url,
        description,
    )
    if not score["accepted"]:
        return None

    row = {
        "retailerSlug": target["retailerSlug"],
        "retailerName": target["retailerName"],
        "regionCode": REGION_CODE,
        "country": target["country"],
        "platform": target["platform"],
        "sourceUrl": product_url,
        "productTitle": f"{brand_name} {name}".strip(),
        "productUrl": product_url,
        "productImageUrl": urljoin(product_url, image_url) if image_url else "",
        "vendor": brand_name,
        "brand": brand_name,
        "priceAmount": price,
        "priceCurrency": target.get("priceCurrency", "USD"),
        "availability": is_available,
        "isAvailable": is_available,
        "stockStatus": stock_status,
        "sku": sku,
        "sourceSnippet": description[:1000],
        "parseConfidence": score["parseConfidence"],
        "discoveryStatus": "accepted",
        "filterReasons": score["filterReasons"],
    }
    normalised = normalise_row(row)
    return {
        **row,
        "brand": normalised.get("brandName") or brand_name,
        "model": normalised.get("modelName") or "",
        "lengthFeetInches": normalised.get("lengthFeetInches"),
        "volumeLitres": normalised.get("volumeLitres"),
    }


def discover_target(target: dict, _max_pages: int) -> dict:
    if target.get("regionCode") != REGION_CODE:
        raise RuntimeError(
            f"US custom discovery requires RegionCode 'US', got {target.get('regionCode')!r}."
        )

    listing_fetches = []
    product_urls: list[str] = []
    for url in target.get("categoryUrls", []):
        response = fetch_html(url)
        listing_fetches.append(
            {
                "url": url,
                "status": "ok" if response["ok"] else "http_error",
                "httpStatus": response["httpStatus"],
                "finalUrl": response["finalUrl"],
                "reason": response["error"],
                "responseBytes": response["responseBytes"],
                "attempts": response["attempts"],
            }
        )
        if response["ok"]:
            product_urls.extend(parse_listing_handles(response["text"]))

    accepted = []
    product_fetches = []
    for product_url in sorted(set(product_urls)):
        response = fetch_html(product_url)
        product_fetches.append(
            {
                "url": product_url,
                "status": "ok" if response["ok"] else "http_error",
                "httpStatus": response["httpStatus"],
                "finalUrl": response["finalUrl"],
                "reason": response["error"],
                "responseBytes": response["responseBytes"],
                "attempts": response["attempts"],
            }
        )
        if not response["ok"]:
            continue
        row = parse_product_json_ld(response["text"], product_url, target)
        if row:
            accepted.append(row)

    products = dedupe_rows(accepted)
    return {
        "target": target["retailerSlug"],
        "pagesCrawled": sum(1 for fetch in listing_fetches if fetch["status"] == "ok"),
        "rawCategoryRows": len(product_urls),
        "uniqueCanonicalProducts": len(products),
        "paginationMethod": "Configured Wix board inventory pages with per-product JSON-LD detail fetch",
        "productsAccepted": len(products),
        "productsRejected": max(len(set(product_urls)) - len(products), 0),
        "fetches": listing_fetches + product_fetches,
        "products": products,
    }


def load_targets() -> list[dict]:
    return json.loads(INPUT_FILE.read_text(encoding="utf-8"))


def selected_targets(targets: list[dict], run_enabled: bool, target_slug: str) -> list[dict]:
    selected = [target for target in targets if run_enabled and target.get("enabled") is True]
    if target_slug:
        selected = [target for target in selected if target.get("retailerSlug") == target_slug]
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover US custom/high-value surfboard products without SQL writes.")
    parser.add_argument("--run-enabled", action="store_true", help="Fetch enabled targets. Without this, no network calls run.")
    parser.add_argument("--target", default="", help="Optional retailerSlug filter.")
    parser.add_argument("--max-pages", type=int, default=0, help="Reserved for interface compatibility.")
    args = parser.parse_args()

    targets = load_targets()
    targets_to_run = selected_targets(targets, args.run_enabled, args.target)
    results = [discover_target(target, max(0, args.max_pages)) for target in targets_to_run]
    products = [product for result in results for product in result["products"]]

    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "run_enabled" if args.run_enabled else "dry_run",
        "purpose": "US custom/high-value product discovery only. No SQL import or production table writes.",
        "targetsConfigured": len(targets),
        "targetsSelected": len(targets_to_run),
        "results": [{key: value for key, value in result.items() if key != "products"} for result in results],
        "products": products,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"US custom/high-value discovery: {report['mode']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
