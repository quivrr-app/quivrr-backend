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
SHOP_LIST_URL = "https://chilli.shaperbuddy.com/api/v1/shop/surfboards"
SHOP_DETAIL_URL = "https://chilli.shaperbuddy.com/api/v1/shop/surfboards/{id}"

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
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u0092", "'")
        .replace("\u0093", '"')
        .replace("\u0094", '"')
        .replace('"', "")
    )

    return " ".join(value.split())


def as_float(value):
    if value in [None, ""]:
        return None

    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def parse_price(value):
    return as_float(value)


def first_image(item):
    img_dynamic = item.get("img_dynamic") or {}

    if isinstance(img_dynamic, dict):
        dynamic_image = (
            img_dynamic.get("deck")
            or img_dynamic.get("bottom")
        )

        if dynamic_image:
            return dynamic_image

    img = item.get("img") or {}

    if isinstance(img, dict):
        for _, image_data in img.items():
            if isinstance(image_data, dict):
                image_url = (
                    image_data.get("img_dynamic")
                    or image_data.get("url")
                )

                if image_url:
                    return image_url

    return (
        item.get("img_logo")
        or item.get("img_deck")
        or item.get("img_bottom")
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


def normalise_fin_setup(item):
    fin_system = clean(item.get("finsystem"))
    fin_count = clean(item.get("fin_no"))

    if fin_system and fin_count:
        return f"{fin_system} {fin_count} Fin"

    if fin_system:
        return fin_system

    return None


def build_stock_product_url(stock_id):
    return (
        "https://www.chillisurfboards.com/shop/surfboards/detail.php"
        f"?id={stock_id}&direct=1&region=aus"
    )


def build_catalogue_product_url(model_id):
    return (
        "https://www.chillisurfboards.com/surfboards/detail.php"
        f"?id={model_id}&direct=1&region=aus"
    )


def is_stock_available(item):
    stock_status = clean(item.get("stockstatus"))
    id_stockstatus = clean(item.get("id_stockstatus"))

    if id_stockstatus == "1":
        return True

    if stock_status and stock_status.lower() in ["in stock", "available"]:
        return True

    return False


def is_dimension_available(dimension):
    dimension_available = dimension.get("shopavailable")

    if str(dimension_available).lower() in ["1", "true", "yes", "available"]:
        return True

    current_availability = as_float(dimension.get("currentavailability"))

    if current_availability is not None and current_availability > 0:
        return True

    return False


def fetch_json(url, params=None):
    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=(10, 60),
    )

    response.raise_for_status()

    return response.json()


def fetch_models():
    return fetch_json(MODELS_URL)


def fetch_detail(model_id):
    payload = fetch_json(DETAIL_URL.format(id=model_id))

    if isinstance(payload, list) and payload:
        return payload[0]

    if isinstance(payload, dict):
        return payload

    return {}


def dimensions_match_stock_row(stock_row, dimension):
    length = clean(dimension.get("length_inches"))
    width = clean(dimension.get("width_inches"))
    thickness = clean(dimension.get("thickness_inches"))
    volume = as_float(dimension.get("volume"))

    stock_length = clean(stock_row.get("length_inches"))
    stock_width = clean(stock_row.get("width_inches"))
    stock_thickness = clean(stock_row.get("thickness_inches"))
    stock_volume = as_float(stock_row.get("volume"))

    if length and stock_length and length != stock_length:
        return False

    if width and stock_width and width != stock_width:
        return False

    if thickness and stock_thickness and thickness != stock_thickness:
        return False

    if volume is not None and stock_volume is not None:
        if abs(volume - stock_volume) > 0.15:
            return False

    return True


def fetch_shop_rows_for_model(model_id):
    params = {
        "model": model_id,
    }

    payload = fetch_json(SHOP_LIST_URL, params=params)

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ["data", "rows", "items", "surfboards"]:
            value = payload.get(key)

            if isinstance(value, list):
                return value

    return []


def filter_shop_rows_for_dimension(shop_rows, dimension):
    return [
        row
        for row in shop_rows
        if dimensions_match_stock_row(row, dimension)
    ]


def fetch_shop_detail(stock_id):
    payload = fetch_json(SHOP_DETAIL_URL.format(id=stock_id))

    if isinstance(payload, list) and payload:
        return payload[0]

    if isinstance(payload, dict):
        return payload

    return {}


def build_inventory_row(item, fallback_model_id, fallback_dimension, now):
    stock_id = clean(item.get("id_surfboard"))

    if not stock_id:
        return None

    model_name = clean(item.get("surfboardmodel"))
    length = clean(item.get("length_inches")) or clean(fallback_dimension.get("length_inches"))
    width = clean(item.get("width_inches")) or clean(fallback_dimension.get("width_inches"))
    thickness = clean(item.get("thickness_inches")) or clean(fallback_dimension.get("thickness_inches"))
    volume_litres = as_float(item.get("volume") or fallback_dimension.get("volume"))

    if not model_name or not length or not width or not thickness or volume_litres is None:
        return None

    construction = normalise_construction(
        item.get("surfboardconstructiontype")
        or fallback_dimension.get("surfboardconstructiontype")
    )

    fin_setup = normalise_fin_setup(item)
    is_available = is_stock_available(item)

    source_variant_title = (
        f"{length} x {width} x {thickness} {volume_litres:g}L"
    )

    if fin_setup:
        source_variant_title = f"{source_variant_title} {fin_setup}"

    return {
        "brandName": BRAND_NAME,
        "modelName": model_name,
        "rawProductTitle": f"{BRAND_NAME} {model_name} {source_variant_title}",
        "normalisedProductTitle": f"{BRAND_NAME} {model_name} {source_variant_title}",
        "lengthFeetInches": length,
        "width": width,
        "thickness": thickness,
        "volumeLitres": volume_litres,
        "construction": construction,
        "finSetup": fin_setup,
        "tailShape": clean(item.get("tailname") or fallback_dimension.get("tail")),
        "productUrl": build_stock_product_url(stock_id),
        "productImageUrl": first_image(item),
        "priceAmount": parse_price(item.get("webprice") or item.get("price")),
        "priceCurrency": clean((item.get("currency") or {}).get("iso")) or "AUD",
        "stockStatus": "available" if is_available else "unavailable",
        "isAvailable": is_available,
        "availabilitySource": AVAILABILITY_SOURCE,
        "regionCode": REGION_CODE,
        "sourceProductId": stock_id,
        "sourceVariantId": clean(item.get("id_surfboardmodel")) or clean(fallback_model_id),
        "sourceVariantTitle": source_variant_title,
        "sourceCataloguePath": DETAIL_URL.format(id=fallback_model_id),
        "sourceStorefront": SOURCE_STOREFRONT,
        "snapshotUtc": now,
    }


def row_size_key(row):
    return (
        clean(row.get("modelName")),
        clean(row.get("lengthFeetInches")),
        clean(row.get("width")),
        clean(row.get("thickness")),
        str(as_float(row.get("volumeLitres"))),
        clean(row.get("construction")),
    )


def is_shop_stock_row(row):
    return "/shop/surfboards/detail.php" in str(row.get("productUrl") or "")


def remove_fallback_rows_when_stock_exists(rows):
    stock_keys = {
        row_size_key(row)
        for row in rows
        if is_shop_stock_row(row)
    }

    cleaned_rows = []

    for row in rows:
        if not is_shop_stock_row(row) and row_size_key(row) in stock_keys:
            continue

        cleaned_rows.append(row)

    return cleaned_rows


def build_fallback_row(model_name, model_id, detail, dimension, now):
    length = clean(dimension.get("length_inches"))
    width = clean(dimension.get("width_inches"))
    thickness = clean(dimension.get("thickness_inches"))
    volume_litres = as_float(dimension.get("volume"))

    if not length or not width or not thickness or volume_litres is None:
        return None

    construction = normalise_construction(
        dimension.get("surfboardconstructiontype")
        or detail.get("surfboardconstructiontype")
    )

    return {
        "brandName": BRAND_NAME,
        "modelName": model_name,
        "rawProductTitle": f"{BRAND_NAME} {model_name} {length} {volume_litres:g}L",
        "normalisedProductTitle": f"{BRAND_NAME} {model_name} {length} {volume_litres:g}L",
        "lengthFeetInches": length,
        "width": width,
        "thickness": thickness,
        "volumeLitres": volume_litres,
        "construction": construction,
        "finSetup": None,
        "tailShape": clean(dimension.get("tail")) or clean(detail.get("tailname")),
        "productUrl": build_catalogue_product_url(model_id),
        "productImageUrl": first_image(detail),
        "priceAmount": parse_price(dimension.get("baseprice") or detail.get("min_price_web") or detail.get("min_price")),
        "priceCurrency": "AUD",
        "stockStatus": "available",
        "isAvailable": True,
        "availabilitySource": AVAILABILITY_SOURCE,
        "regionCode": REGION_CODE,
        "sourceProductId": clean(model_id),
        "sourceVariantId": clean(dimension.get("id")),
        "sourceVariantTitle": f"{length} x {width} x {thickness} {volume_litres:g}L",
        "sourceCataloguePath": DETAIL_URL.format(id=model_id),
        "sourceStorefront": SOURCE_STOREFRONT,
        "snapshotUtc": now,
    }


def main():
    models = fetch_models()
    now = datetime.now(timezone.utc).isoformat()

    output_rows = []
    failures = []
    skipped_unavailable_dimensions = 0
    skipped_missing_dimensions = 0
    shop_rows_seen = 0
    shop_rows_used = 0
    fallback_rows = 0
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
                "stage": "detail",
                "error": str(exc),
            })
            continue

        dimensions = detail.get("standard_dimensions") or []

        if not dimensions:
            failures.append({
                "model_id": model_id,
                "model_name": model_name,
                "stage": "dimensions",
                "error": "No standard dimensions",
            })
            continue

        try:
            model_shop_rows = fetch_shop_rows_for_model(model_id)
        except Exception as exc:
            failures.append({
                "model_id": model_id,
                "model_name": model_name,
                "stage": "shop_model_list",
                "error": str(exc),
            })
            model_shop_rows = []

        for dimension in dimensions:
            if not is_dimension_available(dimension):
                skipped_unavailable_dimensions += 1
                continue

            length = clean(dimension.get("length_inches"))
            width = clean(dimension.get("width_inches"))
            thickness = clean(dimension.get("thickness_inches"))
            volume_litres = as_float(dimension.get("volume"))

            if not length or not width or not thickness or volume_litres is None:
                skipped_missing_dimensions += 1
                continue

            shop_rows = filter_shop_rows_for_dimension(
                model_shop_rows,
                dimension,
            )

            shop_rows_seen += len(shop_rows)
            matched_shop_rows = []

            for shop_row in shop_rows:
                stock_id = clean(shop_row.get("id_surfboard"))

                if not stock_id:
                    continue

                row = build_inventory_row(
                    shop_row,
                    model_id,
                    dimension,
                    now,
                )

                if not row:
                    continue

                if not row.get("isAvailable"):
                    continue

                dedupe_key = (
                    row.get("sourceProductId"),
                    row.get("modelName"),
                    row.get("lengthFeetInches"),
                    row.get("width"),
                    row.get("thickness"),
                    str(row.get("volumeLitres")),
                    row.get("construction"),
                    row.get("finSetup"),
                )

                if dedupe_key in seen:
                    continue

                seen.add(dedupe_key)
                output_rows.append(row)
                matched_shop_rows.append(row)
                shop_rows_used += 1

                time.sleep(0.05)

            if not matched_shop_rows:
                fallback = build_fallback_row(
                    model_name,
                    model_id,
                    detail,
                    dimension,
                    now,
                )

                if fallback:
                    dedupe_key = (
                        fallback.get("sourceProductId"),
                        fallback.get("sourceVariantId"),
                        fallback.get("modelName"),
                        fallback.get("lengthFeetInches"),
                        fallback.get("width"),
                        fallback.get("thickness"),
                        str(fallback.get("volumeLitres")),
                        fallback.get("construction"),
                    )

                    if dedupe_key not in seen:
                        seen.add(dedupe_key)
                        output_rows.append(fallback)
                        fallback_rows += 1

            time.sleep(0.1)

    before_cleanup_rows = len(output_rows)
    output_rows = remove_fallback_rows_when_stock_exists(output_rows)
    removed_fallback_rows = before_cleanup_rows - len(output_rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Chilli AU manufacturer availability build complete")
    print(f"Models seen: {len(models)}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Shop rows seen: {shop_rows_seen}")
    print(f"Shop rows used: {shop_rows_used}")
    print(f"Fallback rows: {fallback_rows}")
    print(f"Removed fallback rows where stock exists: {removed_fallback_rows}")
    print(f"Skipped unavailable dimensions: {skipped_unavailable_dimensions}")
    print(f"Skipped missing dimensions: {skipped_missing_dimensions}")
    print(f"Failures: {len(failures)}")
    print(f"Output: {OUTPUT_PATH}")

    if failures:
        print("")
        print("Failures:")
        for failure in failures[:30]:
            print(failure)


if __name__ == "__main__":
    main()
