import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    )
}


RETAILERS = [
    {
        "name": "Natural Necessity",
        "url": "https://naturalnecessity.com.au",
    },
    {
        "name": "Surf FX",
        "url": "https://surffx.com.au",
    },
    {
        "name": "Strapper Surf",
        "url": "https://strapper.com.au",
    },
    {
        "name": "Southern Man",
        "url": "https://www.southernman.com.au",
    },
    {
        "name": "Coopers Board Store",
        "url": "https://coopersboardstore.com.au",
    },
    {
        "name": "The Surfboard Warehouse",
        "url": "https://www.thesurfboardwarehouse.com.au",
    },
    {
        "name": "The Board Lab",
        "url": "https://www.theboardlab.com.au",
    },
    {
        "name": "Welcome Boardstore",
        "url": "https://welcomeboardstore.com.au",
    },
]


OUTPUT_PATH = Path(
    "scrapers/retailers/priority_retailer_discovery.json"
)


def detect_platform(html, url):
    html_lower = html.lower()

    if "cdn.shopify.com" in html_lower:
        return "shopify"

    if "woocommerce" in html_lower or "/wp-content/" in html_lower:
        return "woocommerce"

    if "bigcommerce" in html_lower:
        return "bigcommerce"

    if "squarespace" in html_lower:
        return "squarespace"

    if "maropost" in html_lower or "neto" in html_lower:
        return "neto_maropost"

    if "magento" in html_lower:
        return "magento"

    return "unknown"


def check_endpoint(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
            verify=False,
        )

        return {
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type"),
            "length": len(response.text),
        }

    except Exception as exc:
        return {
            "error": str(exc)
        }


def discover(retailer):
    name = retailer["name"]
    base_url = retailer["url"]

    print(f"\n{name}")
    print("=" * 60)

    result = {
        "name": name,
        "url": base_url,
    }

    try:
        response = requests.get(
            base_url,
            headers=HEADERS,
            timeout=30,
            verify=False,
        )

        html = response.text

        result["homepage_status"] = response.status_code
        result["platform"] = detect_platform(html, base_url)

        print(f"Homepage: {response.status_code}")
        print(f"Detected platform: {result['platform']}")

        soup = BeautifulSoup(html, "html.parser")

        links = []

        for tag in soup.find_all("a", href=True):
            href = tag["href"]

            if "/products/" in href:
                links.append(href)

            if "/product/" in href:
                links.append(href)

        result["sample_product_links"] = links[:10]

        shopify_endpoint = (
            f"{base_url.rstrip('/')}/products.json?limit=5"
        )

        wc_endpoint = (
            f"{base_url.rstrip('/')}"
            "/wp-json/wc/store/products?per_page=5"
        )

        result["shopify_test"] = check_endpoint(shopify_endpoint)
        result["woocommerce_test"] = check_endpoint(wc_endpoint)

        print("Shopify endpoint checked")
        print("WooCommerce endpoint checked")

    except Exception as exc:
        result["error"] = str(exc)
        print(f"FAILED: {exc}")

    return result


def main():
    results = []

    for retailer in RETAILERS:
        results.append(discover(retailer))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_PATH.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print("\n")
    print("=" * 60)
    print("Discovery complete")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()