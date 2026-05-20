import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests


BRAND_NAME = "JS Industries"
REGION_CODE = "AU"
BASE_URL = "https://jsindustries.com"
PRODUCTS_URL = "https://jsindustries.com/products.json?limit=250"
OUTPUT_FILE = Path("scrapers/manufacturers/availability/output/js_industries/js_au_manufacturer_inventory.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}


def clean(value):
    value = str(value or "")
    value = value.replace("’", "'").replace("‘", "'")
    value = value.replace("″", '"').replace("”", '"').replace("“", '"')
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def normalise_length(value):
    value = clean(value)

    if not value:
        return None

    value = value.replace('"', "")

    match = re.search(r"([4-9])['’]\s*(\d{1,2})", value)

    if not match:
        return None

    return f"{match.group(1)}'{match.group(2)}"


def normalise_volume(value):
    value = clean(value)

    if not value:
        return None

    patterns = [
        r"(\\d{2}(?:\\.\\d+)?)\\s*[lL]\\b",
        r"(\\d{2}(?:\\.\\d+)?)\\s*litres?",
        r"(\\d{2}(?:\\.\\d+)?)\\s*liters?",
    ]

    for pattern in patterns:
        match = re.search(pattern, value, re.IGNORECASE)

        if not match:
            continue

        try:
            volume = float(match.group(1))

            if 15 <= volume <= 100:
                return volume

        except Exception:
            pass

    return None



def extract_js_model_name(value):
    value = clean(value) or ""

    match = re.search(
        r"\bJS\s+(.+?)\s+-\s+[4-9]['?]\s*\d{1,2}",
        value,
        re.IGNORECASE,
    )

    if match:
        return clean(match.group(1))

    return None


def extract_dimension_parts(value):
    value = clean(value) or ""

    match = re.search(
        r"([4-9]['?]\s*\d{1,2}(?:\"?1/2)?)\s*[xX]\s*"
        r"(\d{1,2}(?:\s+\d{1,2}/\d{1,2})?)\"?\s*[xX]\s*"
        r"(\d(?:\s+\d{1,2}/\d{1,2})?)\"?",
        value,
        re.IGNORECASE,
    )

    if not match:
        return None, None, None

    length = normalise_length(match.group(1))
    width = clean(match.group(2))
    thickness = clean(match.group(3))

    return length, width, thickness


def detect_construction(text):
    text = clean(text) or ""
    lower = text.lower()

    if "hyfi" in lower:
        return "HYFI"
    if "carbotune" in lower or "carbon tune" in lower:
        return "CarboTune"
    if "pu" in lower:
        return "PU"
    if "eps" in lower:
        return "EPS"

    return None


def fetch_products():
    response = requests.get(PRODUCTS_URL, headers=HEADERS, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data.get("products", [])


def product_image(product):
    images = product.get("images") or []

    if images:
        src = images[0].get("src")

        if src:
            return src

    image = product.get("image") or {}

    if image.get("src"):
        return image.get("src")

    return None


def is_board_product(product):
    title = clean(product.get("title")) or ""
    product_type = clean(product.get("product_type")) or ""
    tags = " ".join(product.get("tags") or [])

    combined = f"{title} {product_type} {tags}".lower()

    reject_terms = [
        "tee",
        "shirt",
        "hat",
        "cap",
        "deck grip",
        "traction",
        "pad",
        "fins",
        "fin",
        "leash",
        "cover",
        "bag",
        "wax",
        "sticker",
        "gift card",
    ]

    if any(term in combined for term in reject_terms):
        return False

    board_terms = [
        "surfboard",
        "board",
        "shortboard",
        "fish",
        "step up",
        "mid length",
        "longboard",
        "hyfi",
        "carbotune",
        "pu",
    ]

    return any(term in combined for term in board_terms)


def parse_variant(product, variant):
    product_title = clean(product.get("title"))
    variant_title = clean(variant.get("title"))
    combined = " ".join([x for x in [product_title, variant_title] if x])

    parsed_model_name = extract_js_model_name(combined) or product_title
    length, width, thickness = extract_dimension_parts(combined)
    volume = normalise_volume(combined)
    construction = detect_construction(combined)

    available = bool(variant.get("available"))

    inventory_quantity = variant.get("inventory_quantity")

    if inventory_quantity is not None:
        try:
            available = available or int(inventory_quantity) > 0
        except Exception:
            pass

    price = variant.get("price")

    try:
        price_amount = float(price) if price is not None else None
    except Exception:
        price_amount = None

    handle = clean(product.get("handle")) or ""
    product_url = urljoin(BASE_URL, f"/products/{handle}") if handle else BASE_URL

    return {
        "brand": BRAND_NAME,
        "regionCode": REGION_CODE,
        "brandName": BRAND_NAME,
        "modelName": parsed_model_name,
        "rawProductTitle": combined,
        "normalisedProductTitle": combined,
        "productUrl": product_url,
        "productImageUrl": product_image(product),
        "lengthFeetInches": length,
        "width": width,
        "thickness": thickness,
        "volumeLitres": volume,
        "construction": construction,
        "finSetup": None,
        "priceAmount": price_amount,
        "priceCurrency": "AUD",
        "stockStatus": "available" if available else "unavailable",
        "isAvailable": available,
        "source": "js_industries_shopify_products_json",
        "sourcePayload": {
            "product_id": product.get("id"),
            "variant_id": variant.get("id"),
            "product_title": product_title,
            "variant_title": variant_title,
            "available": variant.get("available"),
            "inventory_quantity": inventory_quantity,
            "sku": variant.get("sku"),
        },
        "scrapedAtUtc": datetime.now(timezone.utc).isoformat(),
    }


def main():
    print("")
    print("Building JS Industries AU manufacturer availability")
    print(f"Source: {PRODUCTS_URL}")

    products = fetch_products()

    rows = []

    for product in products:
        if not is_board_product(product):
            continue

        variants = product.get("variants") or []

        for variant in variants:
            row = parse_variant(product, variant)

            if not row["lengthFeetInches"] and not row["volumeLitres"]:
                continue

            rows.append(row)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    available_count = sum(1 for row in rows if row["isAvailable"])

    print("")
    print("JS Industries AU manufacturer availability complete")
    print(f"Rows: {len(rows)}")
    print(f"Available rows: {available_count}")
    print(f"Output: {OUTPUT_FILE}")

    if not rows:
        raise RuntimeError("No JS Industries manufacturer availability rows built")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"JS Industries availability build failed: {exc}")
        sys.exit(1)
