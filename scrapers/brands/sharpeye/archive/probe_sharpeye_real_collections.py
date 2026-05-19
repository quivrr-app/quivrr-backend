import json
from pathlib import Path

import requests


BASE_URL = "https://sharpeyesurfboards.com"

COLLECTIONS = [
    "performance-range",
    "pro-range",
    "hv-range",
    "xl-range",
    "alternate-range",
    "youth-range",
]

OUTPUT_FILE = Path("scrapers/brands/sharpeye/output/sharpeye_real_collection_probe.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Referer": BASE_URL,
}

results = []

print("")
print("=" * 100)
print("SHARP EYE REAL COLLECTION PROBE")
print("=" * 100)

for collection in COLLECTIONS:

    url = f"{BASE_URL}/collections/{collection}/products.json?limit=250"

    row = {
        "collection": collection,
        "url": url,
        "status_code": None,
        "product_count": 0,
        "titles": [],
    }

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=(10, 30),
        )

        row["status_code"] = response.status_code

        print("")
        print("Collection:", collection)
        print("Status:", response.status_code)

        if response.status_code == 200:

            data = response.json()
            products = data.get("products", [])

            row["product_count"] = len(products)

            for product in products:
                title = product.get("title")

                if title:
                    row["titles"].append(title)

            print("Products:", len(products))

            for title in row["titles"][:25]:
                print(" -", title)

    except Exception as exc:

        row["error"] = str(exc)

        print("ERROR:", exc)

    results.append(row)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
