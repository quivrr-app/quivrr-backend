import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("scrapers/brands/channel_islands/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    "https://shop-au.cisurfboards.com/collections/board-models",
    "https://shop-au.cisurfboards.com/collections/all-products",
    "https://shop-au.cisurfboards.com/collections/ect",
    "https://shop-au.cisurfboards.com/collections/spine-tek",
    "https://cisurfboards.com/collections/board-models",
    "https://cisurfboards.com/collections/ect",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)"
}


def fetch(url: str) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=30)

    item = {
        "url": url,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "length": len(response.text),
        "title": None,
        "product_links": [],
        "json_script_count": 0,
        "contains_dims_token": "{{ dims.volume }}" in response.text,
        "contains_shopify_products_json_hint": "/products/" in response.text,
        "sample_text": None,
    }

    soup = BeautifulSoup(response.text, "html.parser")

    if soup.title:
        item["title"] = soup.title.get_text(" ", strip=True)

    text = soup.get_text(" ", strip=True)
    item["sample_text"] = text[:1200]

    for script in soup.find_all("script"):
        script_text = script.get_text(" ", strip=True)
        if "Product" in script_text or "variants" in script_text or "dims" in script_text:
            item["json_script_count"] += 1

    links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/products/" in href:
            if href.startswith("/"):
                href = "https://shop-au.cisurfboards.com" + href

            links.append(href.split("?")[0])

    item["product_links"] = sorted(set(links))[:100]

    return item


def main() -> None:
    results = []

    for url in TARGETS:
        print(f"Checking {url}")
        try:
            results.append(fetch(url))
        except Exception as exc:
            results.append(
                {
                    "url": url,
                    "error": str(exc),
                }
            )

    output_path = OUTPUT_DIR / "channel_islands_recon_report.json"
    output_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("")
    print(f"Wrote {output_path}")

    for result in results:
        print("")
        print(result.get("url"))
        print(f"Status: {result.get('status_code')}")
        print(f"Title: {result.get('title')}")
        print(f"Product links found: {len(result.get('product_links', []))}")
        print(f"JSON script hints: {result.get('json_script_count')}")
        print(f"Dims token present: {result.get('contains_dims_token')}")


if __name__ == "__main__":
    main()
