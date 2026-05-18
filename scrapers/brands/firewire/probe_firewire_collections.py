import json
from pathlib import Path

import requests


BASE_URL = "https://www.firewiresurfboards.com"

COLLECTIONS = [
    "prestige-surfboards",
    "surfboards",
    "all",
]

OUTPUT_FILE = Path("scrapers/brands/firewire/output/firewire_collection_probe.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


results = []

print("")
print("=" * 80)
print("FIREWIRE COLLECTION PROBE")
print("=" * 80)

for collection in COLLECTIONS:
    url = f"{BASE_URL}/collections/{collection}/products.json?limit=10"

    row = {
        "collection": collection,
        "url": url,
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

            print("Products:", len(products))

            samples = []

            for product in products[:10]:
                sample = {
                    "title": product.get("title"),
                    "handle": product.get("handle"),
                    "variant_count": len(product.get("variants", [])),
                    "variant_titles": [
                        variant.get("title")
                        for variant in product.get("variants", [])[:12]
                    ],
                }

                samples.append(sample)

                print("")
                print("Title:", sample["title"])
                print("Handle:", sample["handle"])
                print("Variants:", sample["variant_count"])

                for title in sample["variant_titles"]:
                    print(" -", title)

            row["samples"] = samples

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
