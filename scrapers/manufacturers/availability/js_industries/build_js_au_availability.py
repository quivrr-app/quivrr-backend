import json
import logging
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://jsindustries.com/",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def clean(value):
    if value is None:
        return None

    value = str(value)
    value = value.replace("â€™", "'")
    value = value.replace("â€˜", "'")
    value = value.replace("’", "'")
    value = value.replace("`", "'")
    value = value.replace("â€œ", '"')
    value = value.replace("â€", '"')
    value = value.replace("â€³", '"')
    value = value.replace("“", '"')
    value = value.replace("”", '"')
    value = re.sub(r"\s+", " ", value).strip()

    return value or None


def normalise_length(value):
    value = clean(value)

    if not value:
        return None

    value = value.replace('"', "")
    value = value.replace(" ", "")

    half_match = re.search(r"([4-9])'(\d{1,2})1/2", value)

    if half_match:
        return f"{half_match.group(1)}'{int(half_match.group(2))} 1/2"

    match = re.search(r"([4-9])'(\d{1,2})", value)

    if not match:
        return None

    return f"{match.group(1)}'{int(match.group(2))}"


def parse_dimensions(value):
    value = clean(value) or ""

    match = re.search(
        r"(?P<length>[4-9]'\d{1,2}(?:\s*1/2)?)[\"]?\s*[xX]\s*"
        r"(?P<width>\d{1,2}(?:\s+\d{1,2}/\d{1,2})?)[\"]?\s*[xX]\s*"
        r"(?P<thickness>\d(?:\s+\d{1,2}/\d{1,2})?)[\"]?",
        value,
        re.IGNORECASE,
    )

    if not match:
        return None, None, None

    return (
        normalise_length(match.group("length")),
        clean(match.group("width")),
        clean(match.group("thickness")),
    )


def normalise_volume(value):
    value = clean(value)

    if not value:
        return None

    patterns = [
        r"(\d{2}(?:\.\d+)?)\s*[lL]\b",
        r"(\d{2}(?:\.\d+)?)\s*litres?",
        r"(\d{2}(?:\.\d+)?)\s*liters?",
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
            continue

    return None


def detect_construction(value):
    value = clean(value) or ""
    lower = value.lower()

    if "carbotune" in lower or "carbon tune" in lower:
        return "CarboTune"

    if "hyfi" in lower:
        return "HYFI"

    if re.search(r"\bpu\b", lower):
        return "PU"

    if re.search(r"\beps\b", lower):
        return "EPS"

    if re.search(r"\bpe\b", lower):
        return "PE"

    return None


def product_image(product):
    images = product.get("images") or []

    if images and images[0].get("src"):
        return images[0].get("src")

    image = product.get("image") or {}

    if image.get("src"):
        return image.get("src")

    return None


def fetch_products():
    logging.info("Fetching JS products from %s", PRODUCTS_URL)

    response = requests.get(
        PRODUCTS_URL,
        headers=HEADERS,
        timeout=60,
    )

    response.raise_for_status()

    products = response.json().get("products") or []

    logging.info("Fetched %s JS products", len(products))

    return products


def is_excluded_product(product, variant=None):
    title = clean(product.get("title")) or ""
    handle = clean(product.get("handle")) or ""
    product_type = clean(product.get("product_type")) or ""
    tags = " ".join(product.get("tags") or "")
    variant_title = clean((variant or {}).get("title")) or ""

    combined = f"{title} {handle} {product_type} {tags} {variant_title}".lower()

    blocked_terms = [
        "custom-order",
        "custom order",
        "made to order",
        "made-to-order",
        "gift card",
        "deck grip",
        "traction",
        "tail pad",
        "fins set",
        "fin set",
        "leash",
        "cover",
        "board bag",
        "tee",
        "shirt",
        "hat",
        "cap",
        "sticker",
        "wax",
    ]

    return any(term in combined for term in blocked_terms)


def looks_like_board(product):
    title = clean(product.get("title")) or ""
    product_type = clean(product.get("product_type")) or ""
    tags = " ".join(product.get("tags") or "")
    combined = f"{title} {product_type} {tags}".lower()

    if is_excluded_product(product):
        return False

    if re.search(r"[4-9]'\d{1,2}", combined):
        return True

    board_terms = [
        "surfboard",
        "shortboard",
        "fish",
        "step up",
        "mid length",
        "longboard",
        "hyfi",
        "carbotune",
        "pu",
        "eps",
    ]

    return any(term in combined for term in board_terms)


def parse_model_from_title(title):
    title = clean(title) or ""

    match = re.search(
        r"^(?P<model>.+?)\s+[4-9]'\d{1,2}",
        title,
        re.IGNORECASE,
    )

    if match:
        return clean(match.group("model"))

    match = re.search(
        r"\bJS\s+(?P<model>.+?)\s+-\s+[4-9]'\d{1,2}",
        title,
        re.IGNORECASE,
    )

    if match:
        return clean(match.group("model"))

    return title or None


def parse_variant(product, variant):
    product_title = clean(product.get("title")) or ""
    variant_title = clean(variant.get("title")) or ""
    combined = " ".join([x for x in [product_title, variant_title] if x])

    length, width, thickness = parse_dimensions(combined)
    volume = normalise_volume(combined)
    construction = detect_construction(combined)
    model_name = parse_model_from_title(product_title)

    available = bool(variant.get("available"))

    inventory_quantity = variant.get("inventory_quantity")

    if inventory_quantity is not None:
        try:
            inventory_quantity = int(inventory_quantity)
            available = available or inventory_quantity > 0
        except Exception:
            logging.warning("Unable to parse inventory quantity for %s", combined)

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
        "modelName": model_name,
        "rawProductTitle": combined,
        "normalisedProductTitle": combined,
        "productUrl": product_url,
        "productImageUrl": product_image(product),
        "length": length,
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
        "availabilitySource": "manufacturer_direct",
        "source": "js_industries_shopify_products_json",
        "sourcePayload": {
            "product_id": product.get("id"),
            "variant_id": variant.get("id"),
            "product_title": product_title,
            "variant_title": variant_title,
            "available": variant.get("available"),
            "inventory_quantity": variant.get("inventory_quantity"),
            "sku": variant.get("sku"),
        },
        "scrapedAtUtc": datetime.now(timezone.utc).isoformat(),
    }


def build_rows(products):
    rows = []
    skipped_not_board = 0
    skipped_excluded = 0
    skipped_no_dimensions = 0
    skipped_unknown_model = 0
    failed_variants = 0

    for product in products:
        if not looks_like_board(product):
            skipped_not_board += 1
            continue

        variants = product.get("variants") or []

        if not variants:
            logging.warning("Skipping product with no variants: %s", product.get("title"))
            continue

        for variant in variants:
            try:
                if is_excluded_product(product, variant):
                    skipped_excluded += 1
                    continue

                row = parse_variant(product, variant)

                if not row.get("modelName"):
                    skipped_unknown_model += 1
                    continue

                if not row.get("length") and not row.get("volumeLitres"):
                    skipped_no_dimensions += 1
                    logging.debug("Skipping no dimensions: %s", row.get("rawProductTitle"))
                    continue

                rows.append(row)

            except Exception as ex:
                failed_variants += 1
                logging.exception("Failed to parse JS variant: %s error=%s", product.get("title"), ex)

    logging.info("Rows built: %s", len(rows))
    logging.info("Skipped not board: %s", skipped_not_board)
    logging.info("Skipped excluded: %s", skipped_excluded)
    logging.info("Skipped no dimensions: %s", skipped_no_dimensions)
    logging.info("Skipped unknown model: %s", skipped_unknown_model)
    logging.info("Failed variants: %s", failed_variants)

    missing_length = sum(1 for row in rows if not row.get("length"))
    custom_order_rows = sum(1 for row in rows if "custom-order" in (row.get("productUrl") or "").lower())

    logging.info("Rows missing length: %s", missing_length)
    logging.info("Custom order rows retained: %s", custom_order_rows)

    if custom_order_rows:
        raise RuntimeError("Custom order rows were retained, aborting JS availability build")

    return rows


def main():
    logging.info("Building JS Industries AU manufacturer availability")
    logging.info("Source: %s", PRODUCTS_URL)

    products = fetch_products()
    rows = build_rows(products)

    if not rows:
        raise RuntimeError("No JS Industries manufacturer availability rows built")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    available_count = sum(1 for row in rows if row.get("isAvailable"))

    logging.info("JS Industries AU manufacturer availability complete")
    logging.info("Rows: %s", len(rows))
    logging.info("Available rows: %s", available_count)
    logging.info("Output: %s", OUTPUT_FILE)

    print("")
    print("JS Industries AU manufacturer availability complete")
    print(f"Rows: {len(rows)}")
    print(f"Available rows: {available_count}")
    print(f"Output: {OUTPUT_FILE}")

    if any(not row.get("length") for row in rows):
        print("")
        print("WARNING: Some JS rows still have no length. Check logs before committing.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("JS Industries availability build failed")
        print(f"JS Industries availability build failed: {exc}")
        sys.exit(1)
