import json
from pathlib import Path

import requests


BASE = "https://rustysurfboards.com"

CANDIDATE_COLLECTIONS = [
    "all-shortboards",
    "all-alternatives",
    "surfboards",
    "shortboards",
    "fish",
    "mid-length",
    "step-up",
    "guns",
    "twins",
    "performance",
    "hybrids",
    "boards",
]

OUTPUT_FILE = Path("scrapers/brands/rusty/output/rusty_collection_probe.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


results = []

print("")
print("=" * 100)
print("RUSTY COLLECTION PROBE")
print("=" * 100)

for collection in CANDIDATE_COLLECTIONS:

    url = f"{BASE}/collections/{collection}/products.json?limit=10"

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

        if response.status_code == 200:

            data = response.json()

            products = data.get("products", [])

            row["product_count"] = len(products)

            titles = []

            for product in products[:20]:
                titles.append(product.get("title"))

            row["sample_titles"] = titles

            print("")
            print(collection)
            print("Products:", len(products))

            for title in titles[:10]:
                print(" -", title)

        else:
            row["error"] = response.text[:300]

            print("")
            print(collection)
            print("Status:", response.status_code)

    except Exception as exc:

        row["error"] = str(exc)

        print("")
        print(collection)
        print("ERROR:", exc)

    results.append(row)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
