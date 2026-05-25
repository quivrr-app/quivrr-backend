import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

SOURCE_PATH = Path("scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json")
OUTPUT_PATH = Path("scrapers/manufacturers/availability/output/pyzel/pyzel_au_manufacturer_inventory.json")

BRAND_NAME = "Pyzel"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"
PYZEL_AU_BASE_URL = "https://pyzelsurf.com.au"


def normalise_text(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value)

    return value


def normalise_construction(value, model=None, title=None):
    combined = " ".join([
        str(value or ""),
        str(model or ""),
        str(title or ""),
    ]).lower()

    if "electralite plus" in combined or "electralite+" in combined:
        return "ElectraLite Plus"

    if "electralite" in combined or "electra lite" in combined:
        return "ElectraLite"

    if "soft" in combined:
        return "Soft Top"

    if "eps" in combined:
        return "EPS"

    if "pu" in combined:
        return "PU"

    return normalise_text(value) or "PU"


def normalise_fin_system(value, title=None):
    combined = " ".join([
        str(value or ""),
        str(title or ""),
    ]).lower()

    if "fcs ii" in combined or "fcs2" in combined or "fcsii" in combined:
        return "FCS II"

    if "future" in combined:
        return "Futures"

    value = normalise_text(value)

    if value:
        return value

    return None


def is_valid_volume(value):
    if value is None:
        return True

    try:
        value = float(value)
    except Exception:
        return False

    return 10.0 <= value <= 70.0


def build_au_product_url(base_url, variant_id):
    base_url = normalise_text(base_url)

    if not base_url:
        return None

    try:
        parsed = urlparse(base_url)
        path = parsed.path or ""

        if path.startswith("/products/"):
            parsed = parsed._replace(
                scheme="https",
                netloc="pyzelsurf.com.au",
                query="",
                fragment="",
            )
            base_url = urlunparse(parsed)
    except Exception:
        pass

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
    skipped_invalid_volume = 0
    seen = set()

    for row in rows:
        if row.get("is_active") is False:
            continue

        model = normalise_text(row.get("model"))
        length = normalise_text(row.get("length"))
        width = normalise_text(row.get("width"))
        thickness = normalise_text(row.get("thickness"))
        volume_litres = row.get("volume_litres")
        source_title = normalise_text(row.get("source_product_title"))
        construction = normalise_construction(row.get("construction"), model, source_title)
        fin_system = normalise_fin_system(row.get("fin_system"), source_title)
        variant_id = row.get("source_variant_id")
        product_url = build_au_product_url(row.get("official_product_url"), variant_id)

        if not model or not length or not product_url:
            continue

        if not is_valid_volume(volume_litres):
            skipped_invalid_volume += 1
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
            "tailShape": row.get("tail_shape"),
            "productUrl": product_url,
            "productImageUrl": row.get("official_image_url") or row.get("image_url") or row.get("image"),
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
            "sourceStorefront": PYZEL_AU_BASE_URL,
            "snapshotUtc": now,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output_rows, indent=2), encoding="utf-8")

    print("Pyzel AU manufacturer availability build complete")
    print(f"Source rows: {len(rows)}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Skipped invalid volume: {skipped_invalid_volume}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
