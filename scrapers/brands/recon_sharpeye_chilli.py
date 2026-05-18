import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BRANDS = {
    "SharpEye": [
        "https://www.sharpeyesurfboards.com",
        "https://au.sharpeyesurfboards.com",
    ],
    "Chilli": [
        "https://www.chillisurfboards.com",
    ],
}

OUTPUT_FILE = Path("scrapers/brands/recon_sharpeye_chilli.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


def detect_platform(html):
    lowered = html.lower()

    if "shopify" in lowered:
        return "Shopify"

    if "woocommerce" in lowered or "wp-content" in lowered:
        return "WooCommerce/WordPress"

    if "squarespace" in lowered:
        return "Squarespace"

    return "Unknown"


results = []

print("")
print("=" * 80)
print("SHARPEYE + CHILLI RECON")
print("=" * 80)

for brand, urls in BRANDS.items():
    for url in urls:
        row = {
            "brand": brand,
            "url": url,
        }

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=(10, 30),
            )

            soup = BeautifulSoup(response.text, "html.parser")

            row["status_code"] = response.status_code
            row["final_url"] = response.url
            row["platform"] = detect_platform(response.text)
            row["title"] = soup.title.get_text(" ", strip=True) if soup.title else None

            row["products_json"] = "/products.json" in response.text
            row["wp_content"] = "wp-content" in response.text
            row["shopify"] = "shopify" in response.text.lower()

            print("")
            print("=" * 80)
            print(brand)
            print("=" * 80)
            print("URL:", url)
            print("Final URL:", response.url)
            print("Status:", response.status_code)
            print("Platform:", row["platform"])
            print("Title:", row["title"])

        except Exception as exc:
            row["error"] = str(exc)

            print("")
            print("=" * 80)
            print(brand)
            print("=" * 80)
            print("URL:", url)
            print("ERROR:", exc)

        results.append(row)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
