import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests


SOURCE_PATH = Path("scrapers/brands/haydenshapes/output/haydenshapes_master_catalogue_clean.json")
OUTPUT_PATH = Path("scrapers/manufacturers/availability/output/haydenshapes/haydenshapes_au_manufacturer_inventory.json")

BRAND_NAME = "Haydenshapes"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"
HAYDENSHAPES_AU_BASE_URL = "https://au.haydenshapes.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "application/json,text/html,application/xhtml+xml",
}


def normalise_text(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value)

    return value


def normalise_key(value):
    value = normalise_text(value) or ""
    value = value.lower()
    value = value.replace('"', "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalise_construction(value, title=None, description=None):
    combined = " ".join([
        str(value or ""),
        str(title or ""),
        str(description or ""),
    ]).lower()

    if "futureflex" in combined or "future flex" in combined:
        return "FutureFlex"

    if "pu" in combined:
        return "PU"

    if "pe" in combined:
        return "PE"

    if "eps" in combined:
        return "EPS"

    return normalise_text(value) or None


def is_valid_volume(value):
    if value is None:
        return True

    try:
        value = float(value)
    except Exception:
        return False

    return 10.0 <= value <= 90.0


def clean_product_url(url):
    url = normalise_text(url)

    if not url:
        return None

    try:
        parsed = urlparse(url)
        parsed = parsed._replace(
            scheme="https",
            netloc="au.haydenshapes.com",
            query="",
            fragment="",
        )
        return urlunparse(parsed)
    except Exception:
        return url


def product_json_url(product_url):
    product_url = clean_product_url(product_url)

    if not product_url:
        return None

    parsed = urlparse(product_url)
    path = parsed.path or ""

    if not path.startswith("/products/"):
        return None

    handle = path.split("/products/", 1)[1].strip("/")

    if not handle:
        return None

    return f"{HAYDENSHAPES_AU_BASE_URL}/products/{handle}.json"


def build_au_product_url(base_url, variant_id):
    base_url = clean_product_url(base_url)

    if not base_url:
        return None

    if not variant_id:
        return base_url

    return f"{base_url}?variant={variant_id}"


def parse_int(value):
    if value in [None, ""]:
        return None

    try:
        return int(value)
    except Exception:
        return None


def variant_stock_state(variant):
    available = bool(variant.get("available"))
    inventory_quantity = parse_int(variant.get("inventory_quantity"))
    inventory_policy = normalise_key(variant.get("inventory_policy"))
    inventory_management = normalise_key(variant.get("inventory_management"))

    if available:
        return True, "available"

    if inventory_quantity is not None and inventory_quantity > 0:
        return True, "available"

    if inventory_management in ["", "none", "null"]:
        return True, "available"

    if inventory_policy == "continue":
        return False, "made_to_order"

    return False, "sold_out"


def fetch_product(product_url, cache):
    json_url = product_json_url(product_url)

    if not json_url:
        return None

    if json_url in cache:
        return cache[json_url]

    try:
        response = requests.get(json_url, headers=HEADERS, timeout=(10, 30))
        response.raise_for_status()
        product = response.json().get("product")
        cache[json_url] = product
        time.sleep(0.25)
        return product

    except Exception as exc:
        print(f"Failed to fetch Haydenshapes product JSON: {json_url} :: {exc}")
        cache[json_url] = None
        return None


def find_matching_variant(product, row):
    if not product:
        return None

    variants = product.get("variants") or []
    source_variant_title = normalise_key(row.get("source_variant_title"))

    if source_variant_title:
        for variant in variants:
            if normalise_key(variant.get("title")) == source_variant_title:
                return variant

    row_length = normalise_key(row.get("length_feet_inches"))
    row_width = normalise_key(row.get("width"))
    row_thickness = normalise_key(row.get("thickness"))
    row_volume = row.get("volume_litres")

    for variant in variants:
        variant_title = normalise_key(variant.get("title"))

        if row_length and row_length not in variant_title:
            continue

        if row_width and normalise_key(row_width) not in variant_title:
            continue

        if row_thickness and normalise_key(row_thickness) not in variant_title:
            continue

        if row_volume is not None:
            volume_text = str(float(row_volume)).rstrip("0").rstrip(".")
            if volume_text not in variant_title:
                continue

        return variant

    return None


def main():
    if not SOURCE_PATH.exists():
        raise SystemExit(f"Missing source catalogue file: {SOURCE_PATH}")

    rows = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    now = datetime.now(timezone.utc).isoformat()

    output_rows = []
    skipped_invalid_volume = 0
    unmatched_variants = 0
    product_cache = {}
    seen = set()

    for row in rows:
        if row.get("is_active") is False:
            continue

        model = normalise_text(row.get("model_name"))
        length = normalise_text(row.get("length_feet_inches"))
        width = normalise_text(row.get("width"))
        thickness = normalise_text(row.get("thickness"))
        volume_litres = row.get("volume_litres")
        source_title = normalise_text(row.get("source_product_title") or row.get("source_variant_title"))
        description = normalise_text(row.get("description"))
        construction = normalise_construction(row.get("construction"), source_title, description)

        base_product_url = clean_product_url(row.get("official_product_url"))
        product = fetch_product(base_product_url, product_cache)
        variant = find_matching_variant(product, row)

        if not model or not length or not base_product_url:
            continue

        if not is_valid_volume(volume_litres):
            skipped_invalid_volume += 1
            continue

        if variant:
            variant_id = variant.get("id")
            is_available, stock_status = variant_stock_state(variant)
            price_amount = variant.get("price") or row.get("price_amount")
            product_url = build_au_product_url(base_product_url, variant_id)
        else:
            unmatched_variants += 1
            variant_id = None
            is_available = False
            stock_status = "unknown"
            price_amount = row.get("price_amount")
            product_url = base_product_url

        dedupe_key = (
            model,
            length,
            width,
            thickness,
            str(volume_litres),
            construction,
            str(variant_id),
            product_url,
        )

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)

        output_rows.append({
            "brandName": BRAND_NAME,
            "modelName": model,
            "lengthFeetInches": length,
            "width": width,
            "thickness": thickness,
            "volumeLitres": volume_litres,
            "construction": construction,
            "finSetup": row.get("fin_setup"),
            "tailShape": row.get("tail_shape"),
            "productUrl": product_url,
            "productImageUrl": row.get("official_image_url") or row.get("image_url") or row.get("image"),
            "priceAmount": price_amount,
            "priceCurrency": "AUD",
            "stockStatus": stock_status,
            "isAvailable": is_available,
            "availabilitySource": AVAILABILITY_SOURCE,
            "regionCode": REGION_CODE,
            "sourceProductId": product.get("id") if product else row.get("source_product_id"),
            "sourceVariantId": variant_id,
            "sourceVariantTitle": row.get("source_variant_title"),
            "sourceCataloguePath": str(SOURCE_PATH),
            "sourceStorefront": HAYDENSHAPES_AU_BASE_URL,
            "snapshotUtc": now,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output_rows, indent=2), encoding="utf-8")

    available_count = sum(1 for row in output_rows if row.get("isAvailable"))

    print("Haydenshapes AU manufacturer availability build complete")
    print(f"Source rows: {len(rows)}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Available rows: {available_count}")
    print(f"Unavailable rows: {len(output_rows) - available_count}")
    print(f"Unmatched variants: {unmatched_variants}")
    print(f"Skipped invalid volume: {skipped_invalid_volume}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
