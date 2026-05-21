import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://albumsurf.com/en-au/collections/new-boards/products.json?limit=250"

OUTPUT_FILE = Path(
    "scrapers/manufacturers/availability/output/album/album_au_manufacturer_inventory.json"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def normalise_length(title):
    if not title:
        return None

    match = re.search(r"(\d+)'\s*(\d+)", title)

    if not match:
        return None

    return f"{match.group(1)}'{match.group(2)}"


def product_image(product):
    images = product.get("images") or []

    if not images:
        return None

    return images[0].get("src")


def is_board_product(product):
    product_type = clean(product.get("product_type")).lower()

    return "surfboard" in product_type


def extract_dimensions_from_page(product_url):
    try:
        response = requests.get(
            product_url,
            headers=HEADERS,
            timeout=60,
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        text_content = soup.get_text(" ", strip=True)

        match = re.search(
            r'(\d+[.]?\d*)\s*[\'"]?\s*x\s*(\d+[.]?\d*)\s*[\'"]?\s*x\s*(\d+[.]?\d*)\s*[\'"]?.*?\((\d+[.]?\d*)\s*Liters\)',
            text_content,
            re.IGNORECASE,
        )

        if not match:
            return None, None, None

        return match.group(2), match.group(3), float(match.group(4))

    except Exception as ex:
        print(f"Dimension extraction failed for {product_url}: {ex}")

        return None, None, None


print("")
print("Building Album AU manufacturer availability")
print(f"Source: {SOURCE_URL}")

response = requests.get(
    SOURCE_URL,
    headers=HEADERS,
    timeout=60,
)

response.raise_for_status()

products = response.json().get("products") or []

rows = []

for product in products:
    try:
        if not is_board_product(product):
            continue

        title = clean(product.get("title"))

        if not title:
            continue

        variant = (product.get("variants") or [{}])[0]
        product_url = f"https://albumsurf.com/en-au/products/{product.get('handle')}"

        width, thickness, litres = extract_dimensions_from_page(product_url)

        available = bool(variant.get("available"))
        price = variant.get("price")

        rows.append({
            "brandName": "Album",
            "modelName": clean(variant.get("title")) or title,
            "length": normalise_length(title),
            "width": width,
            "thickness": thickness,
            "volumeLitres": litres,
            "construction": None,
            "stockStatus": "available" if available else "sold_out",
            "isAvailable": available,
            "priceAmount": float(price) if price else None,
            "priceCurrency": "AUD",
            "productUrl": product_url,
            "productImageUrl": product_image(product),
            "availabilitySource": "manufacturer_direct",
            "regionCode": "AU",
        })

    except Exception as ex:
        print(f"Failed Album product: {ex}")

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE.write_text(
    json.dumps(rows, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

available_rows = [
    row for row in rows
    if row.get("isAvailable")
]

print("")
print("Album AU manufacturer availability complete")
print(f"Rows: {len(rows)}")
print(f"Available rows: {len(available_rows)}")
print(f"Output: {OUTPUT_FILE}")

if not rows:
    raise SystemExit("No Album manufacturer availability rows built")
