import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

BRAND_NAME = "Misfit Shapes"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"
SOURCE_STOREFRONT = "https://misfitshapes.com"

SHOPIFY_PRODUCTS_URL = (
    "https://misfitshapes.com/collections/current-models/products.json"
)

CATALOGUE_PATH = Path(
    "scrapers/brands/misfit/output/misfit_master_catalogue_clean.json"
)

OUTPUT_PATH = Path(
    "scrapers/manufacturers/availability/output/misfit/misfit_au_manufacturer_inventory.json"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = (
        value
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace('"', "")
    )

    return " ".join(value.split())


def normalise_key(value):
    value = clean(value) or ""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def parse_variant_length(value):
    value = clean(value) or ""

    match = re.search(r"\b(\d+'\d+)\b", value)

    if match:
        return match.group(1)

    return None


def parse_tail_shape(value):
    value = clean(value) or ""
    lowered = value.lower()

    if "swallow" in lowered:
        return "Swallow"

    if "round" in lowered:
        return "Round"

    if "squash" in lowered:
        return "Squash"

    if "pin" in lowered:
        return "Pin"

    return None


def money(value):
    if value in [None, ""]:
        return None

    try:
        return round(float(value), 2)
    except Exception:
        return None


def product_image(product):
    images = product.get("images") or []

    if images:
        return images[0].get("src")

    return None


def build_product_url(handle, variant_id=None):
    url = f"{SOURCE_STOREFRONT}/collections/current-models/products/{handle}"

    if variant_id:
        url = f"{url}?variant={variant_id}"

    return url


def load_catalogue():
    rows = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))

    index = {}

    for row in rows:
        if not row.get("is_active", True):
            continue

        model = row.get("model")
        length = row.get("length")

        if not model or not length:
            continue

        key = (
            normalise_key(model),
            clean(length),
        )

        index.setdefault(key, []).append(row)

    return index


def fetch_products():
    response = requests.get(
        SHOPIFY_PRODUCTS_URL,
        headers=HEADERS,
        timeout=(10, 60),
    )

    response.raise_for_status()

    return response.json().get("products", [])


def main():
    catalogue_index = load_catalogue()
    products = fetch_products()
    now = datetime.now(timezone.utc).isoformat()

    rows = []
    skipped_non_board = 0
    skipped_unavailable = 0
    skipped_no_length = 0
    skipped_no_catalogue_match = 0
    seen = set()

    for product in products:
        product_type = clean(product.get("product_type")) or ""
        tags = product.get("tags") or []

        if product_type.lower() != "surfboard":
            skipped_non_board += 1
            continue

        model_name = clean(product.get("title"))
        handle = product.get("handle")
        image_url = product_image(product)

        if not model_name or not handle:
            continue

        variants = product.get("variants") or []

        for variant in variants:
            if not variant.get("available"):
                skipped_unavailable += 1
                continue

            variant_title = clean(variant.get("title"))
            length = parse_variant_length(variant_title)

            if not length:
                skipped_no_length += 1
                continue

            key = (
                normalise_key(model_name),
                length,
            )

            canonical_rows = catalogue_index.get(key) or []

            if not canonical_rows:
                skipped_no_catalogue_match += 1
                continue

            price_amount = money(variant.get("price"))
            variant_id = variant.get("id")
            tail_shape = parse_tail_shape(variant_title)

            for canonical in canonical_rows:
                dedupe_key = (
                    model_name,
                    length,
                    canonical.get("width"),
                    canonical.get("thickness"),
                    str(canonical.get("volume_litres")),
                    canonical.get("construction"),
                    str(variant_id),
                )

                if dedupe_key in seen:
                    continue

                seen.add(dedupe_key)

                rows.append({
                    "brandName": BRAND_NAME,
                    "modelName": canonical.get("model") or model_name,
                    "lengthFeetInches": canonical.get("length"),
                    "width": canonical.get("width"),
                    "thickness": canonical.get("thickness"),
                    "volumeLitres": canonical.get("volume_litres"),
                    "construction": canonical.get("construction"),
                    "finSetup": None,
                    "tailShape": tail_shape or canonical.get("tail_shape"),
                    "productUrl": build_product_url(handle, variant_id),
                    "productImageUrl": image_url or canonical.get("official_image_url"),
                    "priceAmount": price_amount,
                    "priceCurrency": "AUD",
                    "stockStatus": "available",
                    "isAvailable": True,
                    "availabilitySource": AVAILABILITY_SOURCE,
                    "regionCode": REGION_CODE,
                    "sourceProductId": product.get("id"),
                    "sourceVariantId": variant_id,
                    "sourceVariantTitle": variant_title,
                    "sourceCataloguePath": str(CATALOGUE_PATH),
                    "sourceStorefront": SOURCE_STOREFRONT,
                    "snapshotUtc": now,
                })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Misfit AU manufacturer availability build complete")
    print(f"Products seen: {len(products)}")
    print(f"Output rows: {len(rows)}")
    print(f"Skipped non board products: {skipped_non_board}")
    print(f"Skipped unavailable variants: {skipped_unavailable}")
    print(f"Skipped no length: {skipped_no_length}")
    print(f"Skipped no catalogue match: {skipped_no_catalogue_match}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
