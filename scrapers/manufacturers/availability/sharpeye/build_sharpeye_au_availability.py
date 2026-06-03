import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import requests


SOURCE_PATH = Path("scrapers/brands/sharpeye/output/sharpeye_master_catalogue_clean.json")
OUTPUT_PATH = Path("scrapers/manufacturers/availability/output/sharpeye/sharpeye_au_manufacturer_inventory.json")
REPORT_PATH = Path("scrapers/manufacturers/availability/output/sharpeye/sharpeye_au_manufacturer_inventory_report.json")

BRAND_NAME = "Sharp Eye"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"
BASE_URL = "https://www.sharpeyesurfboards.com.au"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json,text/html,*/*",
    "Referer": BASE_URL,
}


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace("×", "x")
    value = value.replace("\\", "")
    value = value.replace("’", "'")
    value = value.replace("‘", "'")
    value = value.replace("“", '"')
    value = value.replace("”", '"')
    value = value.replace("Â", "")
    value = value.replace("â€“", "-")
    value = value.replace("&quot;", '"')
    value = re.sub(r"\s+", " ", value)

    return value.strip() or None


def normalise_for_match(value):
    value = clean(value) or ""
    value = value.lower()
    value = value.replace('"', "")
    value = value.replace(" ", "")
    value = value.replace("litres", "l")
    value = value.replace("liters", "l")
    return value


def normalise_construction(value, title=None, description=None):
    combined = " ".join([
        str(value or ""),
        str(title or ""),
        str(description or ""),
    ]).upper()

    if "C1 LITE" in combined or "C1-LITE" in combined or "C1 CARBON" in combined or "C1-CARBON" in combined:
        return "C1 Lite"

    if "E3 LITE" in combined or "E3-LITE" in combined or "E3 EPS" in combined or "E3-EPS" in combined:
        return "E3 Lite"

    if "PU" in combined:
        return "PU"

    return clean(value) or "PU"


def normalise_fin_system(value, title=None, description=None):
    combined = " ".join([
        str(value or ""),
        str(title or ""),
        str(description or ""),
    ]).upper()

    if "FCS II" in combined or "FCS 2" in combined or "FCS2" in combined:
        return "FCS II"

    if "FUTURES" in combined:
        return "Futures"

    return clean(value)


def to_float(value):
    if value is None:
        return None

    try:
        return float(Decimal(str(value).replace(",", "").strip()))
    except Exception:
        return None


def normalise_price(value):
    amount = to_float(value)

    if amount is None:
        return None

    raw = str(value).strip()

    if "." not in raw and amount > 10000:
        amount = amount / 100

    return round(amount, 2)


def is_valid_volume(value):
    value = to_float(value)

    if value is None:
        return True

    return 10.0 <= value <= 90.0


def handle_from_url(url):
    url = clean(url)

    if not url:
        return None

    try:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]

        if len(parts) >= 2 and parts[0] == "products":
            return parts[1]
    except Exception:
        return None

    return None


def canonical_product_url(row):
    handle = handle_from_url(row.get("official_product_url"))

    if handle:
        return f"{BASE_URL}/products/{handle}"

    url = clean(row.get("official_product_url"))

    if url and "sharpeyesurfboards.com.au" in url:
        return url.split("?")[0].rstrip("/")

    return None


def fetch_product(handle):
    if not handle:
        return None

    urls = [
        f"{BASE_URL}/products/{handle}.js",
        f"{BASE_URL}/products/{handle}.json",
    ]

    for url in urls:
        for attempt in range(1, 4):
            try:
                response = requests.get(url, headers=HEADERS, timeout=(10, 30))

                if response.status_code == 404:
                    break

                response.raise_for_status()

                data = response.json()

                if isinstance(data, dict) and data.get("product"):
                    return data.get("product")

                if isinstance(data, dict) and data.get("handle"):
                    return data

                return data

            except Exception:
                if attempt == 3:
                    break

                time.sleep(0.5 * attempt)

    return None


def variant_text(variant):
    if not variant:
        return ""

    values = [
        variant.get("title"),
        variant.get("option1"),
        variant.get("option2"),
        variant.get("option3"),
        variant.get("sku"),
        variant.get("name"),
        variant.get("public_title"),
    ]

    return " ".join(str(value or "") for value in values)


def variant_matches_row(variant, row):
    text = normalise_for_match(variant_text(variant))

    if not text:
        return False

    checks = [
        row.get("length_feet_inches"),
        row.get("width"),
        row.get("thickness"),
    ]

    for value in checks:
        value = normalise_for_match(value)

        if value and value not in text:
            return False

    volume = to_float(row.get("volume_litres"))

    if volume is not None:
        volume_candidates = {
            normalise_for_match(f"{volume:g}L"),
            normalise_for_match(f"{volume:.1f}L"),
            normalise_for_match(f"{volume:.2f}L"),
        }

        if not any(candidate in text for candidate in volume_candidates):
            return False

    return True


def find_matching_variant(product, row):
    if not product:
        return None

    variants = product.get("variants") or []

    for variant in variants:
        if variant_matches_row(variant, row):
            return variant

    length = normalise_for_match(row.get("length_feet_inches"))

    if length:
        length_matches = [
            variant for variant in variants
            if length in normalise_for_match(variant_text(variant))
        ]

        if len(length_matches) == 1:
            return length_matches[0]

    return None


def product_image(product, row):
    image = clean(row.get("official_image_url") or row.get("image_url") or row.get("image"))

    if image:
        return image

    if not product:
        return None

    images = product.get("images") or []

    if images:
        first = images[0]

        if isinstance(first, dict):
            return first.get("src")

        return clean(first)

    image = product.get("image")

    if isinstance(image, dict):
        return image.get("src")

    return clean(image)


def variant_available(variant, product):
    if variant is not None:
        if "available" in variant:
            return bool(variant.get("available"))

        if "inventory_quantity" in variant:
            try:
                return int(variant.get("inventory_quantity") or 0) > 0
            except Exception:
                pass

    if product is not None and "available" in product:
        return bool(product.get("available"))

    return False


def variant_price(variant):
    if not variant:
        return None

    for key in ("price", "price_amount", "compare_at_price"):
        price = normalise_price(variant.get(key))

        if price is not None:
            return price

    return None


def build_variant_url(product_url, variant):
    product_url = clean(product_url)

    if not product_url:
        return None

    if not variant:
        return product_url

    variant_id = clean(variant.get("id"))

    if not variant_id:
        return product_url

    return f"{product_url}?variant={variant_id}"


def main():
    if not SOURCE_PATH.exists():
        raise SystemExit(f"Missing source catalogue file: {SOURCE_PATH}")

    rows = json.loads(SOURCE_PATH.read_text(encoding="utf-8-sig"))

    now = datetime.now(timezone.utc).isoformat()

    product_cache = {}
    output_rows = []
    seen = set()

    skipped_no_url = 0
    skipped_invalid_volume = 0
    matched_variants = 0
    available_rows = 0
    priced_rows = 0
    missing_variant_rows = 0

    for row in rows:
        if row.get("is_active") is False:
            continue

        model = clean(row.get("model_name"))
        length = clean(row.get("length_feet_inches"))
        width = clean(row.get("width"))
        thickness = clean(row.get("thickness"))
        volume_litres = row.get("volume_litres")
        source_title = clean(row.get("source_product_title") or row.get("source_variant_title"))
        description = clean(row.get("description"))
        product_url = canonical_product_url(row)

        if not model or not length or not product_url:
            skipped_no_url += 1
            continue

        if not is_valid_volume(volume_litres):
            skipped_invalid_volume += 1
            continue

        handle = handle_from_url(product_url)

        if handle not in product_cache:
            product_cache[handle] = fetch_product(handle)

        product = product_cache.get(handle)
        variant = find_matching_variant(product, row)

        if variant:
            matched_variants += 1
        else:
            missing_variant_rows += 1

        is_available = variant_available(variant, product)
        price_amount = variant_price(variant)

        if is_available:
            available_rows += 1

        if price_amount is not None:
            priced_rows += 1

        construction = normalise_construction(row.get("construction"), source_title, description)
        fin_system = normalise_fin_system(row.get("fin_setup"), source_title, description)
        variant_id = clean(variant.get("id")) if variant else clean(row.get("source_variant_id"))

        final_url = build_variant_url(product_url, variant)

        dedupe_key = (
            model,
            length,
            width,
            thickness,
            str(volume_litres),
            construction,
            fin_system,
            str(variant_id),
            final_url,
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
            "finSetup": fin_system,
            "tailShape": row.get("tail_shape"),
            "productUrl": final_url,
            "productImageUrl": product_image(product, row),
            "priceAmount": price_amount,
            "priceCurrency": "AUD" if price_amount is not None else None,
            "stockStatus": "available" if is_available else "not in stock",
            "isAvailable": bool(is_available),
            "availabilitySource": AVAILABILITY_SOURCE,
            "regionCode": REGION_CODE,
            "sourceProductId": clean(product.get("id")) if product else clean(row.get("source_product_id")),
            "sourceVariantId": variant_id,
            "sourceVariantTitle": clean(variant_text(variant)) if variant else clean(row.get("source_variant_title")),
            "sourceCataloguePath": str(SOURCE_PATH),
            "sourceStorefront": BASE_URL,
            "snapshotUtc": now,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_PATH.write_text(
        json.dumps(output_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    bad_dimension_rows = [
        item for item in output_rows
        if "\\" in str(item.get("lengthFeetInches"))
        or "\\" in str(item.get("width"))
        or "\\" in str(item.get("thickness"))
    ]

    report = {
        "brandName": BRAND_NAME,
        "sourceCataloguePath": str(SOURCE_PATH),
        "sourceStorefront": BASE_URL,
        "sourceRows": len(rows),
        "outputRows": len(output_rows),
        "matchedVariants": matched_variants,
        "missingVariantRows": missing_variant_rows,
        "availableRows": available_rows,
        "pricedRows": priced_rows,
        "skippedNoUrl": skipped_no_url,
        "skippedInvalidVolume": skipped_invalid_volume,
        "badDimensionRows": bad_dimension_rows[:20],
        "badUrlRows": [
            item for item in output_rows
            if "aus.sharpeyesurfboards.com" in str(item.get("productUrl"))
        ],
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("=" * 100)
    print("SHARP EYE AU MANUFACTURER AVAILABILITY COMPLETE")
    print("=" * 100)
    print(f"Source rows: {len(rows)}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Matched variants: {matched_variants}")
    print(f"Missing variant rows: {missing_variant_rows}")
    print(f"Available rows: {available_rows}")
    print(f"Priced rows: {priced_rows}")
    print(f"Skipped no URL: {skipped_no_url}")
    print(f"Skipped invalid volume: {skipped_invalid_volume}")
    print(f"Bad dimension rows: {len(bad_dimension_rows)}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
