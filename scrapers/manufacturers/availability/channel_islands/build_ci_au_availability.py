
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://shop-au.cisurfboards.com"
OUTPUT_PATH = Path("scrapers/manufacturers/availability/output/channel_islands/ci_au_manufacturer_inventory.json")


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clean(value):
    if value is None:
        return None

    value = str(value).replace("\u2019", "'").replace("\u2018", "'")
    value = re.sub(r"\s+", " ", value).strip()

    return value or None


def slugify(value):
    value = clean(value) or ""
    value = value.lower()
    value = value.replace("&", " and ")
    value = value.replace(".", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def normalise_length(value):
    value = clean(value) or ""

    match = re.search(r"([4-9])\s*'\s*(\d{1,2})", value)
    if match:
        return f"{match.group(1)}'{int(match.group(2))}"

    match = re.search(r"\b([4-9])(\d{1,2})\b", value)
    if match:
        return f"{match.group(1)}'{int(match.group(2))}"

    return None


def product_url(handle):
    return f"{BASE_URL}/products/{handle}"


def product_image(product):
    images = product.get("images") or []

    if images:
        src = images[0].get("src")
        if src:
            return src

    image = product.get("image") or {}
    return image.get("src")


def is_surfboard_stock(product):
    title = clean(product.get("title")) or ""
    handle = clean(product.get("handle")) or ""
    product_type = clean(product.get("product_type")) or ""
    vendor = clean(product.get("vendor")) or ""

    combined = f"{title} {handle} {product_type} {vendor}".lower()

    if product_type.lower() not in {
        "surfboard stock",
        "surfboards",
    }:
        return False

    blocked = [
        "leash",
        "traction",
        "tail pad",
        "deck grip",
        "fin",
        "fins",
        "t-shirt",
        "tee",
        "hat",
        "cap",
        "gift",
        "accessory",
    ]

    if any(item in combined for item in blocked):
        return False

    return True


def detect_fin_setup(value):
    value = (clean(value) or "").lower()

    if "fcsii" in value or "fcs ii" in value or "fcs-ii" in value:
        return "FCS II"

    if "futures" in value or "future" in value:
        return "Futures"

    return None


def detect_construction(value):
    value = (clean(value) or "").lower()

    if "spine" in value or "spinetek" in value or "spine-tek" in value:
        return "Spine-Tek"

    if "ect" in value or "eco carbon" in value or "carbon tech" in value:
        return "ECT-Carbon"

    return "PU"


def extract_model_name(title, handle):
    title = clean(title) or ""
    handle = clean(handle) or ""

    working = title

    working = re.sub(r"^[4-9]\s*'\s*\d{1,2}\s+", "", working).strip()
    working = re.sub(r"\s+-\s+FCS\s*II.*$", "", working, flags=re.IGNORECASE).strip()
    working = re.sub(r"\s+-\s+FCSII.*$", "", working, flags=re.IGNORECASE).strip()
    working = re.sub(r"\s+-\s+Futures.*$", "", working, flags=re.IGNORECASE).strip()

    working = re.sub(r"\s+ECT\s+PU$", "", working, flags=re.IGNORECASE).strip()
    working = re.sub(r"\s+ECT$", "", working, flags=re.IGNORECASE).strip()
    working = re.sub(r"\s+PU$", "", working, flags=re.IGNORECASE).strip()

    if working:
        return slugify(working)

    handle_no_length = re.sub(r"^[4-9]\d{1,2}-", "", handle)
    handle_no_length = re.sub(r"-(futures|fcsii|fcs-ii).*$", "", handle_no_length)
    handle_no_length = re.sub(r"-ect(-pu)?$", "", handle_no_length)

    return slugify(handle_no_length)


def fetch_all_products():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 Quivrr CI manufacturer availability"
    })

    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/products.json?limit=250&page={page}"
        response = session.get(url, timeout=60)
        response.raise_for_status()

        data = response.json()
        page_products = data.get("products") or []

        if not page_products:
            break

        products.extend(page_products)
        page += 1

    return products


def parse_product(product):
    title = clean(product.get("title")) or ""
    handle = clean(product.get("handle")) or ""
    variants = product.get("variants") or []

    if not is_surfboard_stock(product):
        return None

    length = normalise_length(title) or normalise_length(handle)
    model_name = extract_model_name(title, handle)

    if not length or not model_name:
        return None

    available = any(variant.get("available") is True for variant in variants)

    price_amount = None

    for variant in variants:
        price = variant.get("price")

        if price is not None:
            try:
                price_amount = float(price)
                break
            except Exception:
                pass

    construction = detect_construction(f"{title} {handle}")
    fin_setup = detect_fin_setup(f"{title} {handle}")

    return {
        "brandName": "Channel Islands",
        "modelName": model_name,
        "length": length,
        "width": None,
        "thickness": None,
        "volumeLitres": None,
        "construction": construction,
        "finSetup": fin_setup,
        "stockStatus": "available" if available else "sold_out",
        "isAvailable": bool(available),
        "priceAmount": price_amount,
        "priceCurrency": "AUD",
        "productUrl": product_url(handle),
        "productImageUrl": product_image(product),
        "availabilitySource": "manufacturer_direct",
        "regionCode": "AU",
        "rawProductTitle": title,
        "source": "ci_au_products_json_paginated",
        "scrapedAtUtc": now_utc(),
    }


def main():
    print("Building Channel Islands AU manufacturer availability")
    print(f"Source: {BASE_URL}/products.json with pagination")

    products = fetch_all_products()

    rows = []

    seen_urls = set()

    for product in products:
        row = parse_product(product)

        if not row:
            continue

        url = row.get("productUrl")

        if url in seen_urls:
            continue

        seen_urls.add(url)
        rows.append(row)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print("")
    print("Channel Islands AU manufacturer availability complete")
    print(f"Products scanned: {len(products)}")
    print(f"Rows: {len(rows)}")
    print(f"Available rows: {sum(1 for row in rows if row.get('isAvailable'))}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
