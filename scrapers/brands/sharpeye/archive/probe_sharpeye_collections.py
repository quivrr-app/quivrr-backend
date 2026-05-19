import json
from pathlib import Path

import requests


BASE_URL = "https://sharpeyesurfboards.com"

COLLECTIONS = [
    "all",
    "surfboards",
    "boards",
    "stock-boards",
    "models",
    "surfboard-models",
    "performance",
    "high-performance",
    "shortboards",
]

OUTPUT_FILE = Path("scrapers/brands/sharpeye/output/sharpeye_collection_probe.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}

results = []

print("")
print("=" * 100)
print("SHARP EYE COLLECTION PROBE")
print("=" * 100)

for collection in COLLECTIONS:
    url = f"{BASE_URL}/collections/{collection}/products.json?limit=250"

    row = {
        "collection": collection,
        "url": url,
        "status_code": None,
        "product_count": 0,
        "sample_titles": [],
        "sample_variants": [],
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        row["status_code"] = response.status_code

        print("")
        print("Collection:", collection)
        print("Status:", response.status_code)

        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])

            row["product_count"] = len(products)
            row["sample_titles"] = [
                product.get("title")
                for product in products[:30]
            ]

            for product in products[:5]:
                row["sample_variants"].append({
                    "product_title": product.get("title"),
                    "handle": product.get("handle"),
                    "product_type": product.get("product_type"),
                    "tags": product.get("tags"),
                    "variants": [
                        {
                            "title": variant.get("title"),
                            "price": variant.get("price"),
                            "available": variant.get("available"),
                            "sku": variant.get("sku"),
                        }
                        for variant in (product.get("variants") or [])[:20]
                    ],
                })

            print("Products:", len(products))

            for title in row["sample_titles"]:
                print(" -", title)

    except Exception as exc:
        row["error"] = str(exc)

        print("")
        print("Collection:", collection)
        print("ERROR:", exc)

    results.append(row)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
