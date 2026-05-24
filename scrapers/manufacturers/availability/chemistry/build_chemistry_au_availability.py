import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

BRAND_NAME = "Chemistry Surfboards"
BASE_URL = "https://chemistrysurfboards.com.au"
OUTPUT_PATH = Path("scrapers/manufacturers/availability/output/chemistry/chemistry_au_manufacturer_inventory.json")

MODEL_MAP = {
    "b-side": "b-side",
    "b-side-ex-team": "b-side",
    "pantera-rosa": "pantera-rosa",
    "summertime-pt-2": "summertime-pt-2",
    "the-23": "the-23",
    "the-zen-4": "the-zen-4",
    "the-zen-4-1": "the-zen-4-1",
    "the-zen-4-stock": "the-zen-4",
    "the-zen-4-6-4": "the-zen-4",
}

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def clean(value):
    if value is None:
        return None

    value = str(value)
    value = value.replace("\u2019", "'").replace("\u2018", "'")
    value = value.replace("\u2032", "'").replace("\u2033", '"')
    value = re.sub(r"\s+", " ", value).strip()

    return value or None

def normalise_length(value):
    value = clean(value) or ""

    match = re.search(r"([4-9])\s*'\s*(\d{1,2})", value)
    if match:
        return f"{match.group(1)}'{int(match.group(2))}"

    match = re.search(r"\b([4-9])\s+(\d{1,2})\b", value)
    if match:
        return f"{match.group(1)}'{int(match.group(2))}"

    match = re.search(r"\b([4-9])(\d{1,2})\b", value)
    if match:
        return f"{match.group(1)}'{int(match.group(2))}"

    return None

def normalise_number_text(value):
    value = clean(value)

    if not value:
        return None

    value = value.replace('"', "")
    value = re.sub(r"\s+", " ", value).strip()

    return value or None

def normalise_volume(value):
    value = clean(value) or ""

    match = re.search(r"(\d{2}(?:\.\d+)?)\s*[lL]\b", value)

    if not match:
        return None

    return float(match.group(1))

def extract_dimensions(value):
    value = clean(value) or ""

    match = re.search(
        r"(?P<length>[4-9]\s*'\s*\d{1,2})\s*\"?\s+"
        r"(?P<width>\d{1,2}(?:\s+\d{1,2}/\d{1,2})?)\s*\"?\s+"
        r"(?P<thickness>\d(?:\s+\d{1,2}/\d{1,2})?)\s*\"?\s+"
        r"(?P<volume>\d{2}(?:\.\d+)?)\s*[lL]",
        value,
        re.IGNORECASE,
    )

    if match:
        return {
            "length": normalise_length(match.group("length")),
            "width": normalise_number_text(match.group("width")),
            "thickness": normalise_number_text(match.group("thickness")),
            "volumeLitres": float(match.group("volume")),
        }

    return {
        "length": normalise_length(value),
        "width": None,
        "thickness": None,
        "volumeLitres": normalise_volume(value),
    }

def detect_construction(value):
    value = (clean(value) or "").lower()

    if "eps" in value or "epoxy" in value:
        return "EPS"

    if "pu" in value or "poly" in value:
        return "PU"

    return "PU"

def product_image(product):
    images = product.get("images") or []

    if images and images[0].get("src"):
        return images[0].get("src")

    image = product.get("image") or {}

    return image.get("src")

def is_surfboard(product):
    title = clean(product.get("title")) or ""
    handle = clean(product.get("handle")) or ""
    product_type = clean(product.get("product_type")) or ""
    vendor = clean(product.get("vendor")) or ""

    combined = f"{title} {handle} {product_type} {vendor}".lower()

    blocked = [
        "leash",
        "traction",
        "tail pad",
        "deck grip",
        "fin",
        "fins",
        "hat",
        "cap",
        "shirt",
        "tee",
        "wax",
        "gift",
        "sticker",
        "bag",
    ]

    if any(item in combined for item in blocked):
        return False

    return True

def fetch_products():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 Quivrr Chemistry AU availability"
    })

    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/products.json?limit=250&page={page}"
        response = session.get(url, timeout=60)

        if response.status_code != 200:
            print(f"Feed stopped at page {page}: HTTP {response.status_code}")
            break

        data = response.json()
        page_products = data.get("products") or []

        if not page_products:
            break

        products.extend(page_products)
        page += 1

    return products

def model_name_from_handle(handle):
    handle = clean(handle) or ""
    return MODEL_MAP.get(handle, handle)

def variant_sort_price(row):
    price = row.get("priceAmount")

    if price is None:
        return 999999.0

    try:
        return float(price)
    except Exception:
        return 999999.0

def build_row(product, variant):
    title = clean(product.get("title")) or ""
    handle = clean(product.get("handle")) or ""
    variant_title = clean(variant.get("title")) or ""
    option1 = clean(variant.get("option1")) or variant_title
    option2 = clean(variant.get("option2")) or ""
    option3 = clean(variant.get("option3")) or ""

    model_name = model_name_from_handle(handle)

    dimensions = extract_dimensions(option1)
    construction = detect_construction(option2)

    if not dimensions["length"]:
        dimensions = extract_dimensions(f"{variant_title} {title} {handle}")

    variant_id = variant.get("id")
    product_url = f"{BASE_URL}/products/{handle}"

    if variant_id:
        product_url = f"{product_url}?variant={variant_id}"

    price_amount = None

    try:
        price_amount = float(variant.get("price"))
    except Exception:
        pass

    return {
        "brandName": BRAND_NAME,
        "modelName": model_name,
        "length": dimensions["length"],
        "width": dimensions["width"],
        "thickness": dimensions["thickness"],
        "volumeLitres": dimensions["volumeLitres"],
        "construction": construction,
        "finSetup": None,
        "stockStatus": "available" if variant.get("available") is True else "sold_out",
        "isAvailable": bool(variant.get("available")),
        "priceAmount": price_amount,
        "priceCurrency": "AUD",
        "productUrl": product_url,
        "productImageUrl": product_image(product),
        "availabilitySource": "manufacturer_direct",
        "regionCode": "AU",
        "rawProductTitle": f"{title} | {variant_title}",
        "source": "chemistry_au_products_json_deduped_variant",
        "scrapedAtUtc": now_utc(),
    }

def main():
    print("Building Chemistry AU manufacturer availability with deduped size construction parsing")
    print(f"Source: {BASE_URL}/products.json")

    products = fetch_products()

    deduped = {}
    raw_variant_count = 0

    for product in products:
        if not is_surfboard(product):
            continue

        handle = clean(product.get("handle")) or ""
        variants = product.get("variants") or []

        for variant in variants:
            raw_variant_count += 1

            row = build_row(product, variant)

            model_name = row.get("modelName")
            length = row.get("length")
            width = row.get("width")
            thickness = row.get("thickness")
            volume = row.get("volumeLitres")
            construction = row.get("construction")

            key = (
                model_name,
                length,
                width,
                thickness,
                volume,
                construction,
            )

            existing = deduped.get(key)

            if existing is None:
                deduped[key] = row
                continue

            if existing.get("isAvailable") is False and row.get("isAvailable") is True:
                deduped[key] = row
                continue

            if existing.get("isAvailable") == row.get("isAvailable"):
                if variant_sort_price(row) < variant_sort_price(existing):
                    deduped[key] = row

        if not variants:
            row = {
                "brandName": BRAND_NAME,
                "modelName": model_name_from_handle(handle),
                "length": normalise_length(handle),
                "width": None,
                "thickness": None,
                "volumeLitres": None,
                "construction": "PU",
                "finSetup": None,
                "stockStatus": "sold_out",
                "isAvailable": False,
                "priceAmount": None,
                "priceCurrency": "AUD",
                "productUrl": f"{BASE_URL}/products/{handle}",
                "productImageUrl": product_image(product),
                "availabilitySource": "manufacturer_direct",
                "regionCode": "AU",
                "rawProductTitle": clean(product.get("title")),
                "source": "chemistry_au_products_json_deduped_variant",
                "scrapedAtUtc": now_utc(),
            }

            key = (
                row["modelName"],
                row["length"],
                row["width"],
                row["thickness"],
                row["volumeLitres"],
                row["construction"],
            )

            deduped[key] = row

    rows = list(deduped.values())

    rows = [
        row
        for row in rows
        if row.get("modelName")
    ]

    rows.sort(key=lambda row: (
        row.get("modelName") or "",
        row.get("length") or "",
        row.get("construction") or "",
        row.get("volumeLitres") or 0,
    ))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print("")
    print("Chemistry AU manufacturer availability complete")
    print(f"Products scanned: {len(products)}")
    print(f"Raw variants scanned: {raw_variant_count}")
    print(f"Rows after dedupe: {len(rows)}")
    print(f"Available rows: {sum(1 for row in rows if row.get('isAvailable'))}")
    print(f"Output: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
