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
LENGTH_SIGNAL_RE = re.compile(r"\b(?P<feet>[5-9])\s*(?:'|ft|’)\s*(?P<inches>\d{1,2})\b", re.I)
VOLUME_SIGNAL_RE = re.compile(
    r"\b(?P<volume>(?:1[5-9]|[2-7]\d|8[0-5])(?:[\.,]\d{1,2})?)\s*(?:liters|liter|litres|litre|ltr|l)\b",
    re.I,
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


def parse_squarespace_listing_handles(html: str, base_url: str) -> list[str]:
    product_urls = []
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.select("a.ProductList-item-link[href]"):
        url = urljoin(base_url, clean(anchor.get("href")))
        if url and url not in product_urls:
            product_urls.append(url)
    return sorted(product_urls)


def load_product_json_ld(html: str) -> dict | None:
    for match in JSON_LD_RE.finditer(html):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if clean(data.get("@type")).lower() == "product":
            return data
    return None


def parse_signal_length(text: str) -> str | None:
    match = LENGTH_SIGNAL_RE.search(clean(text))
    if not match:
        return None
    return f"{int(match.group('feet'))}'{int(match.group('inches'))}"


def parse_signal_volume(text: str) -> float | None:
    match = VOLUME_SIGNAL_RE.search(clean(text))
    if not match:
        return None
    return float(match.group("volume").replace(",", "."))


def parse_product_json_ld(html: str, product_url: str, target: dict) -> dict | None:
    data = load_product_json_ld(html)
    if not data:
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


def parse_squarespace_product_json_ld(html: str, product_url: str, target: dict) -> dict | None:
    data = load_product_json_ld(html)
    if not data:
        return None

    offers = data.get("offers") or data.get("Offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}

    raw_name = clean(data.get("name"))
    store_name = clean(target.get("retailerName"))
    store_hint = clean(re.sub(r"\b(?:surf|shop|co|company)\b\.?", " ", store_name, flags=re.IGNORECASE))
    product_name = raw_name
    if store_hint:
        product_name = re.sub(
            rf"\s+[—–-]\s+.*{re.escape(store_hint)}.*$",
            "",
            raw_name,
            flags=re.IGNORECASE,
        ) or raw_name
    description = clean(data.get("description"))
    image = data.get("image")
    if isinstance(image, list):
        image_url = clean(image[0]) if image else ""
    elif isinstance(image, dict):
        image_url = clean(image.get("url") or image.get("contentUrl"))
    else:
        image_url = clean(image)
    availability = clean(offers.get("availability") or offers.get("Availability")).lower()
    is_available = True if "instock" in availability else False if "outofstock" in availability else None
    stock_status = "in_stock" if is_available is True else "out_of_stock" if is_available is False else ""
    score = classify_product(product_name, product_url, description)
    if not score["accepted"]:
        has_dimension_signal = bool(parse_signal_length(description) or parse_signal_volume(description) is not None)
        if not (
            "/used-surfboards/" in product_url
            and has_dimension_signal
            and clean(offers.get("price"))
        ):
            return None
        score = {
            "accepted": True,
            "parseConfidence": max(score["parseConfidence"], 5),
            "filterReasons": sorted(set(score["filterReasons"] + ["used_surfboard_dimension_signal"])),
        }

    row = {
        "retailerSlug": target["retailerSlug"],
        "retailerName": target["retailerName"],
        "regionCode": REGION_CODE,
        "country": target["country"],
        "platform": target["platform"],
        "sourceUrl": product_url,
        "productTitle": product_name,
        "productUrl": product_url,
        "productImageUrl": image_url,
        "vendor": "",
        "brand": "",
        "priceAmount": clean(offers.get("price")),
        "priceCurrency": clean(offers.get("priceCurrency")) or target.get("priceCurrency", "USD"),
        "availability": is_available,
        "isAvailable": is_available,
        "stockStatus": stock_status,
        "sku": clean(offers.get("sku") or data.get("sku")),
        "sourceSnippet": description[:1000],
        "parseConfidence": score["parseConfidence"],
        "discoveryStatus": "accepted",
        "filterReasons": score["filterReasons"],
    }
    normalised = normalise_row(row)
    brand = normalised.get("brandName") or ""
    if not brand:
        match = re.match(r"^(?P<brand>[A-Za-z0-9&'+.-]+)\b", product_name)
        brand = clean(match.group("brand")) if match else ""

    return {
        **row,
        "brand": brand,
        "model": normalised.get("modelName") or "",
        "lengthFeetInches": normalised.get("lengthFeetInches") or parse_signal_length(description),
        "volumeLitres": normalised.get("volumeLitres")
        if normalised.get("volumeLitres") is not None
        else parse_signal_volume(description),
    }


def discover_target(target: dict, _max_pages: int) -> dict:
    if target.get("regionCode") != REGION_CODE:
        raise RuntimeError(
            f"US custom discovery requires RegionCode 'US', got {target.get('regionCode')!r}."
        )

    listing_fetches = []
    product_urls: list[str] = []
    discovery_type = clean(target.get("discoveryType")) or "wix_product_page"
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
            if discovery_type == "squarespace_product_page":
                product_urls.extend(parse_squarespace_listing_handles(response["text"], url))
            else:
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
        if discovery_type == "squarespace_product_page":
            row = parse_squarespace_product_json_ld(response["text"], product_url, target)
        else:
            row = parse_product_json_ld(response["text"], product_url, target)
        if row:
            accepted.append(row)

    products = dedupe_rows(accepted)
    return {
        "target": target["retailerSlug"],
        "pagesCrawled": sum(1 for fetch in listing_fetches if fetch["status"] == "ok"),
        "rawCategoryRows": len(product_urls),
        "uniqueCanonicalProducts": len(products),
        "paginationMethod": (
            "Configured Squarespace product-list pages with per-product JSON-LD detail fetch"
            if discovery_type == "squarespace_product_page"
            else "Configured Wix board inventory pages with per-product JSON-LD detail fetch"
        ),
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
