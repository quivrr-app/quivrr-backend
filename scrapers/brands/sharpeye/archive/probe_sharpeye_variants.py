import json
from pathlib import Path

import requests


BASE_URL = "https://sharpeyesurfboards.com"

COLLECTIONS = [
    "performance-range",
    "pro-range",
    "hv-range",
    "alternate-range",
    "youth-range",
]

OUTPUT_FILE = Path("scrapers/brands/sharpeye/output/sharpeye_variant_probe.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Referer": BASE_URL,
}

products_by_handle = {}

for collection in COLLECTIONS:
    url = f"{BASE_URL}/collections/{collection}/products.json?limit=250"
    response = requests.get(url, headers=HEADERS, timeout=(10, 30))
    response.raise_for_status()

    for product in response.json().get("products", []):
        handle = product.get("handle")

        if handle:
            products_by_handle[handle] = product

print("")
print("=" * 100)
print("SHARP EYE VARIANT PROBE")
print("=" * 100)
print("Unique products:", len(products_by_handle))

results = []

for handle, product in sorted(products_by_handle.items()):
    variants = product.get("variants") or []

    row = {
        "title": product.get("title"),
        "handle": handle,
        "product_type": product.get("product_type"),
        "tags": product.get("tags"),
        "variants": [
            {
                "title": variant.get("title"),
                "sku": variant.get("sku"),
                "price": variant.get("price"),
                "available": variant.get("available"),
            }
            for variant in variants[:50]
        ],
    }

    results.append(row)

    print("")
    print("PRODUCT:", row["title"])
    print("Handle:", handle)
    print("Type:", row["product_type"])
    print("Tags:", row["tags"])
    print("Variants:", len(variants))

    for variant in row["variants"][:12]:
        print(" -", variant)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
