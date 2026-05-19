import json
from pathlib import Path

import requests


URL = "https://albumsurf.com/collections/all/products.json?limit=5"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


response = requests.get(
    URL,
    headers=HEADERS,
    timeout=(10, 30),
)

data = response.json()

products = data.get("products", [])

print("")
print("=" * 100)
print("ALBUM RAW PRODUCT INSPECTION")
print("=" * 100)

for product in products:

    print("")
    print("-" * 100)
    print("TITLE:", product.get("title"))
    print("TYPE:", product.get("product_type"))
    print("TAGS:", product.get("tags"))
    print("HANDLE:", product.get("handle"))

    variants = product.get("variants") or []

    print("VARIANTS:", len(variants))

    for variant in variants[:5]:
        print("  -", variant.get("title"))

output = Path("scrapers/brands/album/output/album_raw_products.json")

output.write_text(
    json.dumps(products, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", output)
