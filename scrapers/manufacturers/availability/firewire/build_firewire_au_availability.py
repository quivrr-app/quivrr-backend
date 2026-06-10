import json
import re
import requests
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

SOURCE_PATH = Path("scrapers/brands/firewire/output/firewire_master_catalogue_clean.json")
OUTPUT_PATH = Path("scrapers/manufacturers/availability/output/firewire/firewire_au_manufacturer_inventory.json")

BRAND_NAME = "Firewire"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"
FIREWIRE_AU_BASE_URL = "https://aus.firewiresurfboards.com"


def canonical_key(value):
    value = normalise_text(value) or ""
    value = value.lower()
    value = value.replace("+", " plus ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def load_live_au_products():
    live_by_title = {}
    live_by_handle = {}

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    })

    for page in range(1, 10):
        url = f"{FIREWIRE_AU_BASE_URL}/products.json?limit=250&page={page}"

        try:
            response = session.get(url, timeout=30)
        except Exception:
            break

        if response.status_code != 200:
            break

        products = response.json().get("products", [])

        if not products:
            break

        for product in products:
            title = normalise_text(product.get("title"))
            handle = normalise_text(product.get("handle"))

            if not handle:
                continue

            live_by_handle[handle] = handle

            title_key = canonical_key(title)

            if title_key:
                live_by_title[title_key] = handle

    return live_by_title, live_by_handle


def normalise_text(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value)

    return value


def normalise_construction(value, title=None, description=None):
    combined = " ".join([
        str(value or ""),
        str(title or ""),
        str(description or ""),
    ]).lower()

    if (
        ("i-bolic 2.0" in combined or "ibolic 2.0" in combined)
        and "volcanic" in combined
    ):
        return "I-Bolic 2.0 Volcanic"

    if (
        ("i-bolic" in combined or "ibolic" in combined)
        and "volcanic" in combined
    ):
        return "I-Bolic Volcanic"

    if "i-bolic 2.0" in combined or "ibolic 2.0" in combined:
        return "I-Bolic 2.0"

    if "i-bolic" in combined or "ibolic" in combined:
        return "I-Bolic"

    if "volcanic" in combined:
        return "Volcanic"

    if "helium" in combined:
        return "Helium"

    if "timbertek" in combined or "timber tek" in combined:
        return "TimberTek"

    if "thunderbolt" in combined:
        return "Thunderbolt"

    if "g-flex" in combined or "g flex" in combined:
        return "G-Flex"

    if "proflex" in combined or "pro flex" in combined:
        return "Proflex"

    if "fst" in combined:
        return "FST"

    if "lft" in combined:
        return "LFT"

    if "eps" in combined:
        return "EPS"

    return normalise_text(value) or None


def normalise_fin_system(value, title=None, description=None):
    combined = " ".join([
        str(value or ""),
        str(title or ""),
        str(description or ""),
    ]).lower()

    if "fcs ii" in combined or "fcs2" in combined or "fcsii" in combined:
        return "FCS II"

    if "futures" in combined or "future" in combined:
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

    return 10.0 <= value <= 90.0


def build_au_product_url(base_url, handle, variant_id, live_handle=None):
    handle = normalise_text(live_handle) or normalise_text(handle)
    base_url = normalise_text(base_url)

    if handle:
        base_url = f"{FIREWIRE_AU_BASE_URL}/products/{handle}"

    elif base_url:
        try:
            parsed = urlparse(base_url)
            path = parsed.path or ""

            if path.startswith("/products/"):
                parsed = parsed._replace(
                    scheme="https",
                    netloc="aus.firewiresurfboards.com",
                    query="",
                    fragment="",
                )
                base_url = urlunparse(parsed)
        except Exception:
            pass

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
    live_by_title, live_by_handle = load_live_au_products()

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
        source_title = normalise_text(row.get("source_title") or row.get("source_variant_title"))
        description = normalise_text(row.get("description"))
        construction = normalise_construction(row.get("construction"), source_title, description)
        fin_system = normalise_fin_system(row.get("fin_system"), source_title, description)
        variant_id = row.get("source_variant_id")
        source_handle = normalise_text(row.get("source_product_handle"))
        live_handle = live_by_handle.get(source_handle)

        if not live_handle:
            live_handle = live_by_title.get(canonical_key(source_title))
            live_handle = live_handle or live_by_title.get(canonical_key(model))

        product_url = build_au_product_url(
            row.get("official_product_url"),
            source_handle,
            variant_id,
            live_handle,
        )

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
            "sourceStorefront": FIREWIRE_AU_BASE_URL,
            "snapshotUtc": now,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output_rows, indent=2), encoding="utf-8")

    print("Firewire AU manufacturer availability build complete")
    print(f"Source rows: {len(rows)}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Skipped invalid volume: {skipped_invalid_volume}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

