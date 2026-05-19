import json
from pathlib import Path

import requests


URL = "https://albumsurf.com/collections/all/products.json?limit=250"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

response = requests.get(
    URL,
    headers=HEADERS,
    timeout=(10, 30),
)

products = response.json().get("products", [])

surfboards = []

for product in products:
    product_type = str(product.get("product_type") or "").lower()
    tags = product.get("tags") or []
    title = product.get("title") or ""

    if product_type != "surfboard":
        continue

    if any("used" in str(tag).lower() for tag in tags):
        continue

    if "(used)" in title.lower():
        continue

    surfboards.append({
        "title": title,
        "handle": product.get("handle"),
        "product_type": product.get("product_type"),
        "tags": tags,
        "variants": [
            variant.get("title")
            for variant in product.get("variants", [])
        ],
    })

print("")
print("=" * 100)
print("ALBUM NEW SURFBOARDS")
print("=" * 100)
print("Rows:", len(surfboards))

for row in surfboards[:80]:
    print("")
    print(row["title"])
    print("handle:", row["handle"])
    print("variants:", row["variants"][:5])

output = Path("scrapers/brands/album/output/album_new_surfboards_probe.json")

output.write_text(
    json.dumps(surfboards, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", output)
