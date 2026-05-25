import json
import re
from datetime import datetime, timezone
from pathlib import Path

SOURCE_PATH = Path("scrapers/brands/dhd/output/dhd_master_catalogue_clean.json")
OUTPUT_PATH = Path("scrapers/manufacturers/availability/output/dhd/dhd_au_manufacturer_inventory.json")

BRAND_NAME = "DHD"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"


def normalise_text(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value)

    return value


def normalise_construction(value, model=None):
    combined = " ".join([
        str(value or ""),
        str(model or ""),
    ]).lower()

    if "soft" in combined:
        return "Soft Top"

    if "eps" in combined:
        return "EPS"

    if "pu" in combined:
        return "PU"

    return normalise_text(value) or "PU"


def normalise_fin_system(value):
    value = normalise_text(value)

    if not value:
        return None

    lowered = value.lower()

    if "fcs ii" in lowered or "fcs2" in lowered:
        return "FCS II"

    if lowered == "fcs":
        return "FCS"

    if "future" in lowered:
        return "Futures"

    return value


def build_product_url(base_url, variant_id):
    base_url = normalise_text(base_url)

    if not base_url:
        return None

    if not variant_id:
        return base_url

    if "?variant=" in base_url:
        return base_url

    return f"{base_url}?variant={variant_id}"


def main():
    if not SOURCE_PATH.exists():
        raise SystemExit(f"Missing source catalogue file: {SOURCE_PATH}")

    rows = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    now = datetime.now(timezone.utc).isoformat()

    output_rows = []

    seen = set()

    for row in rows:
        model = normalise_text(row.get("model"))
        length = normalise_text(row.get("length"))
        width = normalise_text(row.get("width"))
        thickness = normalise_text(row.get("thickness"))
        volume_litres = row.get("volume_litres")
        construction = normalise_construction(row.get("construction"), model)
        fin_system = normalise_fin_system(row.get("fin_system"))
        variant_id = row.get("source_variant_id")
        product_url = build_product_url(row.get("official_product_url"), variant_id)

        if not model or not product_url:
            continue

        dedupe_key = (
            model,
            length,
            width,
            thickness,
            str(volume_litres),
            construction,
            fin_system,
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
            "finSetup": fin_system,
            "tailShape": None,
            "productUrl": product_url,
            "productImageUrl": row.get("image_url") or row.get("official_image_url") or row.get("image"),
            "priceAmount": row.get("price") or row.get("price_amount"),
            "priceCurrency": "AUD",
            "stockStatus": "available",
            "isAvailable": True,
            "availabilitySource": AVAILABILITY_SOURCE,
            "regionCode": REGION_CODE,
            "sourceProductId": row.get("source_product_id"),
            "sourceVariantId": variant_id,
            "sourceVariantTitle": row.get("source_variant_title"),
            "sourceCataloguePath": str(SOURCE_PATH),
            "snapshotUtc": now,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output_rows, indent=2), encoding="utf-8")

    print("DHD AU manufacturer availability build complete")
    print(f"Source rows: {len(rows)}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
