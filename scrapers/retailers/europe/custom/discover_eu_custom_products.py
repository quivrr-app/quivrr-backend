from __future__ import annotations

import argparse
import json
import sys
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.europe.common.discovery_utils import (  # noqa: E402
    dedupe_rows,
    decorate_rows,
    product_rows_from_daisuke_cards,
    product_rows_from_json_ld,
    product_rows_from_links,
    product_rows_from_structured_thumbnail_cards,
    parse_price,
    strip_tags,
)
from scrapers.retailers.europe.common.fetch_utils import fetch_text  # noqa: E402


INPUT_FILE = Path("scrapers/retailers/europe/custom/eu_custom_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/europe/custom/output/eu_custom_product_discovery.json")

MAGENTO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_browser_html(url: str, timeout_seconds: int = 30) -> dict:
    try:
        response = requests.get(url, headers=MAGENTO_HEADERS, timeout=timeout_seconds)
        return {
            "ok": response.status_code == 200,
            "httpStatus": response.status_code,
            "finalUrl": response.url,
            "text": response.text,
            "reason": "" if response.status_code == 200 else f"HTTP {response.status_code}",
        }
    except requests.RequestException as error:
        return {
            "ok": False,
            "httpStatus": None,
            "finalUrl": url,
            "text": "",
            "reason": f"{type(error).__name__}: {error}",
        }


def product_rows_from_magento_cards(html: str, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for item in soup.select("li.product-item"):
        title_el = item.select_one("a.product-item-link")
        if not title_el or not title_el.get("href"):
            continue
        title = " ".join(title_el.get_text(" ", strip=True).split())
        if not title:
            continue

        price_el = item.select_one(".price")
        image_el = item.select_one("img.product-image-photo, img")
        image_url = ""
        if image_el:
            image_url = (
                image_el.get("data-amsrc")
                or image_el.get("data-src")
                or image_el.get("src")
                or ""
            )

        card_text = " ".join(item.get_text(" ", strip=True).split())
        card_text_lower = card_text.lower()
        is_available = None
        if "añadir al carrito" in card_text_lower or "add to cart" in card_text_lower:
            is_available = True
        elif "no está disponible" in card_text_lower or "out of stock" in card_text_lower:
            is_available = False

        rows.append(
            {
                "productTitle": title,
                "productUrl": urljoin(source_url, title_el.get("href")),
                "productImageUrl": urljoin(source_url, image_url) if image_url else "",
                "brand": "",
                "vendor": "",
                "priceAmount": price_el.get_text(" ", strip=True) if price_el else "",
                "isAvailable": is_available,
                "stockStatus": "in_stock" if is_available is True else "out_of_stock" if is_available is False else "",
                "sku": "",
                "sourceSnippet": strip_tags(card_text)[:1000],
                "sourceUrl": source_url,
            }
        )

    return dedupe_rows(rows)


def discover_target(target: dict, max_pages: int, confirm_blocked: bool = False) -> dict:
    products = []
    rejected = 0
    fetches = []

    urls = target.get("categoryUrls", [])
    if confirm_blocked:
        urls = urls[:1]

    for category_url in urls:
        page = 1
        seen_urls = set()
        visible_pages = math.ceil(
            int(target.get("visibleProductCount") or 0)
            / max(1, int(target.get("pageSize") or 1))
        )
        page_cap = max_pages or (visible_pages + 1 if visible_pages else 0)
        while page_cap <= 0 or page <= page_cap:
            pagination_param = target.get("paginationParam")
            if page > 1 and pagination_param:
                separator = "&" if "?" in category_url else "?"
                source_url = f"{category_url}{separator}{urlencode({pagination_param: page})}"
            else:
                source_url = category_url
            if target.get("platform") == "custom_magento_cards":
                browser_response = fetch_browser_html(source_url)
                response = type("BrowserResponse", (), {
                    "status": "ok" if browser_response["ok"] else "http_error",
                    "http_status": browser_response["httpStatus"],
                    "final_url": browser_response["finalUrl"],
                    "reason": browser_response["reason"],
                    "ok": browser_response["ok"],
                    "text": browser_response["text"],
                })()
            else:
                response = fetch_text(source_url, retries=0)
            fetches.append({
                "url": source_url,
                "status": response.status,
                "httpStatus": response.http_status,
                "finalUrl": response.final_url,
                "reason": response.reason,
            })

            if confirm_blocked or not response.ok:
                break

            if target.get("platform") == "custom_daisuke":
                rows = product_rows_from_daisuke_cards(response.text, source_url)
            elif target.get("platform") == "custom_magento_cards":
                rows = product_rows_from_magento_cards(response.text, source_url)
            elif target.get("platform") == "custom_structured":
                rows = product_rows_from_structured_thumbnail_cards(response.text, source_url)
            else:
                rows = product_rows_from_json_ld(response.text, source_url)
            markers = target.get("productPathMarkers") or ["/en/surfboards/", "/en/"]
            if target.get("platform") not in {"custom_magento_cards", "custom_structured"}:
                rows.extend(product_rows_from_links(response.text, source_url, markers))
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
        "paginationMethod": f"?{target.get('paginationParam')}={{page}} until empty or duplicate page" if target.get("paginationParam") else "configured category routes",
        "productsAccepted": len(unique_products),
        "productsRejected": rejected,
        "fetches": fetches,
        "products": unique_products,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover EU custom/structured surfboard products without SQL writes.")
    parser.add_argument("--run-enabled", action="store_true", help="Fetch enabled targets. Without this, no network calls run.")
    parser.add_argument("--confirm-blocked", action="store_true", help="Fetch one URL for a disabled target only to confirm blocking status.")
    parser.add_argument("--target", default="", help="Optional retailerSlug filter.")
    parser.add_argument("--max-pages", type=int, default=1, help="Reserved for future pagination; currently category URL limited.")
    args = parser.parse_args()

    targets = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    if args.confirm_blocked:
        selected = targets
    else:
        selected = [target for target in targets if args.run_enabled and target.get("enabled") is True]
    if args.target:
        selected = [target for target in selected if target.get("retailerSlug") == args.target]

    results = [discover_target(target, max(0, args.max_pages), args.confirm_blocked) for target in selected]
    products = [product for result in results for product in result["products"]]
    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "confirm_blocked" if args.confirm_blocked else "run_enabled" if args.run_enabled else "dry_run",
        "purpose": "EU custom/structured product discovery only. No SQL import or production table writes.",
        "targetsConfigured": len(targets),
        "targetsSelected": len(selected),
        "results": [{key: value for key, value in result.items() if key != "products"} for result in results],
        "products": products,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"EU custom/structured discovery: {report['mode']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
