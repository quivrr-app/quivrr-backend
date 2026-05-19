import json
from pathlib import Path

import requests


BASE_URL = "https://albumsurf.com"

COLLECTIONS = [
    "all",
    "surfboards",
    "boards",
    "asymmetricals",
    "twins",
    "fish",
]

OUTPUT_FILE = Path("scrapers/brands/album/output/album_collection_probe.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


results = []

print("")
print("=" * 100)
print("ALBUM COLLECTION PROBE")
print("=" * 100)

for collection in COLLECTIONS:

    url = f"{BASE_URL}/collections/{collection}/products.json?limit=250"

    row = {
        "collection": collection,
        "url": url,
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

            print("Products:", len(products))

            titles = []

            for product in products[:40]:
                title = product.get("title")

                if title:
                    titles.append(title)

            row["titles"] = titles

            for title in titles[:25]:
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
