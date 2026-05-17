import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


TARGETS = [
    {
        "name": "Slimes Boardstore",
        "url": "https://www.slimes.com.au/surfboards",
    },
    {
        "name": "Slimes Newcastle",
        "url": "https://www.slimesnewcastle.com.au/",
    },
    {
        "name": "Surfection",
        "url": "https://surfection.com/",
    },
    {
        "name": "Surfection Mosman",
        "url": "https://surfectionmosman.com/",
    },
    {
        "name": "Board Collective",
        "url": "https://boardcollective.com.au/collections/surfboards",
    },
]


OUTPUT_DIR = Path("scrapers/retailers/output/recon")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def safe_get(url, timeout=20):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )

        return {
            "ok": True,
            "url": url,
            "final_url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "server": response.headers.get("server", ""),
            "text_sample": response.text[:5000],
            "headers": dict(response.headers),
        }

    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "error": str(exc),
        }


def get_base_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def detect_platform(page_text, headers):
    text = page_text.lower()
    header_text = json.dumps(headers).lower()

    signals = []

    if "cdn.shopify.com" in text or "shopify" in text or "x-shopify" in header_text:
        signals.append("shopify")

    if "wp-content" in text or "woocommerce" in text or "wc/store" in text:
        signals.append("woocommerce")

    if "bigcommerce" in text or "stencil" in text:
        signals.append("bigcommerce")

    if "magento" in text or "mage/cookies" in text:
        signals.append("magento")

    if "cloudflare" in text or "cf-ray" in header_text:
        signals.append("cloudflare")

    if "perimeterx" in text or "_px" in text:
        signals.append("perimeterx")

    if "access denied" in text or "forbidden" in text:
        signals.append("possible_block")

    if not signals:
        signals.append("unknown")

    return sorted(set(signals))


def count_product_like_links(base_url, page_text):
    soup = BeautifulSoup(page_text, "html.parser")

    links = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if not href:
            continue

        full_url = urljoin(base_url, href)

        if any(part in full_url.lower() for part in ["/products/", "/product/", "/collections/"]):
            links.append(full_url)

    unique_links = sorted(set(links))

    return {
        "count": len(unique_links),
        "sample": unique_links[:20],
    }


def probe_target(target):
    name = target["name"]
    start_url = target["url"]
    base_url = get_base_url(start_url)

    print()
    print(f"Recon: {name}")
    print(start_url)

    page = safe_get(start_url)

    page_text = page.get("text_sample", "")
    headers = page.get("headers", {})

    platform_signals = detect_platform(page_text, headers)

    endpoints = {
        "home": base_url,
        "robots": urljoin(base_url, "/robots.txt"),
        "sitemap": urljoin(base_url, "/sitemap.xml"),
        "shopify_products": urljoin(base_url, "/products.json?limit=250"),
        "shopify_surfboards_collection": urljoin(base_url, "/collections/surfboards/products.json?limit=250"),
        "woocommerce_store_products": urljoin(base_url, "/wp-json/wc/store/products?per_page=100"),
        "woocommerce_v3_probe": urljoin(base_url, "/wp-json/wc/v3/products"),
    }

    endpoint_results = {}

    for key, endpoint_url in endpoints.items():
        result = safe_get(endpoint_url, timeout=15)

        compact = {
            "url": endpoint_url,
            "ok": result.get("ok"),
            "status_code": result.get("status_code"),
            "final_url": result.get("final_url"),
            "content_type": result.get("content_type"),
            "server": result.get("server"),
        }

        text_sample = result.get("text_sample", "")

        if key.startswith("shopify") and result.get("status_code") == 200:
            compact["looks_like_json_products"] = "\"products\"" in text_sample[:1000]

        if key.startswith("woocommerce") and result.get("status_code") == 200:
            compact["looks_like_wc_products"] = "\"id\"" in text_sample[:1000] or "\"name\"" in text_sample[:1000]

        endpoint_results[key] = compact

    product_links = count_product_like_links(base_url, page.get("text_sample", ""))

    result = {
        "name": name,
        "input_url": start_url,
        "base_url": base_url,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "page_status_code": page.get("status_code"),
        "page_final_url": page.get("final_url"),
        "page_content_type": page.get("content_type"),
        "platform_signals": platform_signals,
        "product_link_discovery": product_links,
        "endpoint_results": endpoint_results,
    }

    print(f"Status: {result['page_status_code']}")
    print(f"Final URL: {result['page_final_url']}")
    print(f"Signals: {', '.join(platform_signals)}")
    print(f"Product links found: {product_links['count']}")

    for key, value in endpoint_results.items():
        print(f"{key}: {value.get('status_code')}")

    return result


def main():
    results = []

    for target in TARGETS:
        results.append(probe_target(target))

    output_file = OUTPUT_DIR / "final_five_retailer_recon.json"

    output_file.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print()
    print("Recon complete.")
    print(f"Output written to: {output_file}")


if __name__ == "__main__":
    main()
