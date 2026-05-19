import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


URLS = [
    "https://www.chillisurfboards.com",
    "https://chillisurfboards.com",
    "https://www.chillisurfboards.com/collections/surfboards",
    "https://chillisurfboards.com/collections/surfboards",
    "https://www.chillisurfboards.com/collections/all",
    "https://chillisurfboards.com/collections/all",
]

OUTPUT_FILE = Path("scrapers/brands/chilli/output/chilli_recon.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}


def detect_platform(html):
    lowered = html.lower()

    if "shopify" in lowered:
        return "Shopify"

    if "woocommerce" in lowered:
        return "WooCommerce"

    if "bigcommerce" in lowered:
        return "BigCommerce"

    return "Unknown"


print("")
print("=" * 100)
print("CHILLI SURFBOARDS RECON")
print("=" * 100)

results = []

for url in URLS:
    row = {"url": url}

    try:
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        soup = BeautifulSoup(response.text, "html.parser")

        row["status_code"] = response.status_code
        row["final_url"] = response.url
        row["platform"] = detect_platform(response.text)
        row["title"] = soup.title.get_text(" ", strip=True) if soup.title else None

        print("")
        print("URL:", url)
        print("Final:", response.url)
        print("Status:", response.status_code)
        print("Platform:", row["platform"])
        print("Title:", row["title"])

    except Exception as exc:
        row["error"] = str(exc)

        print("")
        print("URL:", url)
        print("ERROR:", exc)

    results.append(row)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
