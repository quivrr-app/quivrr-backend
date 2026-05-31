import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BRAND_NAME = "Chilli"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"
SOURCE_STOREFRONT = "https://www.chillisurfboards.com"

MODELS_URL = "https://chilli.shaperbuddy.com/api/v1/surfboardmodels"
DETAIL_URL = "https://chilli.shaperbuddy.com/api/v1/surfboardmodels/{id}?lang=en"

OUTPUT_PATH = Path(
    "scrapers/manufacturers/availability/output/chilli/chilli_au_manufacturer_inventory.json"
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


def first_image(detail):
    img_dynamic = detail.get("img_dynamic") or {}
    img = detail.get("img") or {}

    if isinstance(img_dynamic, dict):
        dynamic_image = (
            img_dynamic.get("deck")
            or img_dynamic.get("bottom")
        )

        if dynamic_image:
            return dynamic_image

    if isinstance(img, dict):
        static_image = (
            img.get("deck")
            or img.get("bottom")
        )

        if static_image:
            return static_image

    return (
        detail.get("img_logo")
        or detail.get("img_deck")
        or detail.get("img_bottom")
        or None
    )


def normalise_construction(value):
    value = clean(value) or ""

    lowered = value.lower()

    if "pu" in lowered or "stringer" in lowered:
        return "PU"

    if "eps" in lowered or "epoxy" in lowered or "futureflex" in lowered:
        return "EPS"

    return value or "Standard"


def build_product_url(model_id):
    return (
        "https://www.chillisurfboards.com/surfboards/detail.php"
        f"?id={model_id}&direct=1&region=aus"
    )


def as_float(value):
    if value in [None, ""]:
        return None

    try:
        return float(value)
    except Exception:
        return None


def is_dimension_available(dimension, detail):
    dimension_available = dimension.get("shopavailable")

    if str(dimension_available).lower() in ["1", "true", "yes", "available"]:
        return True

    current_availability = as_float(dimension.get("currentavailability"))

    if current_availability is not None and current_availability > 0:
        return True

    return False


def fetch_models():
    response = requests.get(
        MODELS_URL,
        headers=HEADERS,
        timeout=(10, 60),
    )

    response.raise_for_status()

    return response.json()


def fetch_detail(model_id):
    response = requests.get(
        DETAIL_URL.format(id=model_id),
        headers=HEADERS,
        timeout=(10, 60),
    )

    response.raise_for_status()

    payload = response.json()

    if isinstance(payload, list) and payload:
        return payload[0]

    if isinstance(payload, dict):
        return payload

    return {}


def main():
    models = fetch_models()
    now = datetime.now(timezone.utc).isoformat()

    output_rows = []
    failures = []
    skipped_unavailable = 0
    skipped_missing_dimensions = 0
    seen = set()

    for model in models:
        model_id = model.get("id_surfboardmodel")
        model_name = clean(model.get("surfboardmodel"))

        if not model_id or not model_name:
            continue

        try:
            detail = fetch_detail(model_id)
        except Exception as exc:
            failures.append({
                "model_id": model_id,
                "model_name": model_name,
                "error": str(exc),
            })
            continue

        dimensions = detail.get("standard_dimensions") or []

        if not dimensions:
            failures.append({
                "model_id": model_id,
                "model_name": model_name,
                "error": "No standard dimensions",
            })
            continue

        product_url = build_product_url(model_id)
        image_url = first_image(detail)
        model_price = as_float(
            detail.get("min_price_web")
            or detail.get("min_price")
            or model.get("min_price_web")
            or model.get("min_price")
        )

        for dimension in dimensions:
            is_available = is_dimension_available(dimension, detail)

            if not is_available:
                skipped_unavailable += 1
                continue

            length = clean(dimension.get("length_inches"))
            width = clean(dimension.get("width_inches"))
            thickness = clean(dimension.get("thickness_inches"))
            volume_litres = as_float(dimension.get("volume"))

            if not length or not width or not thickness or volume_litres is None:
                skipped_missing_dimensions += 1
                continue

            construction = normalise_construction(
                dimension.get("surfboardconstructiontype")
                or detail.get("surfboardconstructiontype")
                or model.get("surfboardconstructiontype")
            )

            price_amount = as_float(dimension.get("baseprice")) or model_price

            dedupe_key = (
                model_name,
                length,
                width,
                thickness,
                str(volume_litres),
                construction,
                str(dimension.get("id")),
            )

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)

            output_rows.append({
                "brandName": BRAND_NAME,
                "modelName": model_name,
                "lengthFeetInches": length,
                "width": width,
                "thickness": thickness,
                "volumeLitres": volume_litres,
                "construction": construction,
                "finSetup": None,
                "tailShape": clean(dimension.get("tail")) or clean(detail.get("tailname")),
                "productUrl": product_url,
                "productImageUrl": image_url,
                "priceAmount": price_amount,
                "priceCurrency": "AUD",
                "stockStatus": "available" if is_available else "unavailable",
                "isAvailable": is_available,
                "availabilitySource": AVAILABILITY_SOURCE,
                "regionCode": REGION_CODE,
                "sourceProductId": model_id,
                "sourceVariantId": dimension.get("id"),
                "sourceVariantTitle": (
                    f"{length} x {width} x {thickness} {volume_litres}L"
                ),
                "sourceCataloguePath": DETAIL_URL.format(id=model_id),
                "sourceStorefront": SOURCE_STOREFRONT,
                "snapshotUtc": now,
            })

        time.sleep(0.15)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Chilli AU manufacturer availability build complete")
    print(f"Models seen: {len(models)}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Skipped unavailable dimensions: {skipped_unavailable}")
    print(f"Skipped missing dimensions: {skipped_missing_dimensions}")
    print(f"Failures: {len(failures)}")
    print(f"Output: {OUTPUT_PATH}")

    if failures:
        print("")
        print("Failures:")
        for failure in failures[:20]:
            print(failure)


if __name__ == "__main__":
    main()
