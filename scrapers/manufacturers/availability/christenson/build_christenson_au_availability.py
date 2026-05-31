import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

BRAND_NAME = "Christenson"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"
SOURCE_STOREFRONT = "https://christensonsurfboards.com.au"
PRODUCTS_URL = "https://christensonsurfboards.com.au/products.json"

OUTPUT_PATH = Path(
    "scrapers/manufacturers/availability/output/christenson/christenson_au_manufacturer_inventory.json"
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
        .replace('\\"', '"')
    )

    return " ".join(value.split())


def money(value):
    if value in [None, ""]:
        return None

    try:
        return round(float(value), 2)
    except Exception:
        return None


def first_image(product):
    images = product.get("images") or []

    if images:
        return images[0].get("src")

    return None


def build_product_url(handle, variant_id=None):
    url = f"{SOURCE_STOREFRONT}/products/{handle}"

    if variant_id:
        url = f"{url}?variant={variant_id}"

    return url


def normalise_fin_setup(value):
    value = clean(value) or ""
    lowered = value.lower()

    if "fcs 2" in lowered or "fcs ii" in lowered or "fcs2" in lowered:
        return "FCS II"

    if "futures" in lowered or "future" in lowered:
        return "Futures"

    if "single" in lowered:
        return "Single"

    if value:
        return value

    return None


def normalise_construction(value):
    value = clean(value) or ""
    lowered = value.lower()

    if "pu" in lowered or "poly" in lowered:
        return "PU"

    if "eps" in lowered or "epoxy" in lowered:
        return "EPS"

    return value or "PU"


def parse_title(title):
    title = clean(title) or ""

    result = {
        "model": None,
        "length": None,
        "width": None,
        "thickness": None,
        "volume": None,
        "tail": None,
        "fin": None,
        "construction": None,
    }

    # Example:
    # OP3 5'10" x 19 1/4" X 2 7/16" - 28.58L, Swallow, 3x FCS 2 Fin Boxes, PU - ID:892566
    pattern = re.compile(
        r"^(?P<model>.+?)\s+"
        r"(?P<length>\d+'\d+)\"?\s*[xX]\s*"
        r"(?P<width>\d+(?:\s+\d+/\d+)?)\"?\s*[xX]\s*"
        r"(?P<thickness>\d+(?:\s+\d+/\d+)?)\"?\s*"
        r"-\s*(?P<volume>\d+(?:\.\d+)?)L"
        r"(?P<rest>.*)$"
    )

    match = pattern.search(title)

    if not match:
        return result

    result["model"] = clean(match.group("model"))
    result["length"] = clean(match.group("length"))
    result["width"] = clean(match.group("width"))
    result["thickness"] = clean(match.group("thickness"))
    result["volume"] = money(match.group("volume"))

    rest = clean(match.group("rest")) or ""

    parts = [
        clean(part)
        for part in rest.split(",")
        if clean(part)
    ]

    for part in parts:
        lowered = part.lower()

        if "fin" in lowered or "fcs" in lowered or "future" in lowered:
            result["fin"] = normalise_fin_setup(part)
            continue

        if lowered in ["pu", "eps", "epoxy", "poly"]:
            result["construction"] = normalise_construction(part)
            continue

        if " id:" in lowered or lowered.startswith("id:"):
            continue

        if any(word in lowered for word in ["swallow", "round", "pin", "squash"]):
            result["tail"] = part

    if not result["construction"]:
        if ", PU" in title or " PU " in title:
            result["construction"] = "PU"
        elif "EPS" in title.upper():
            result["construction"] = "EPS"
        else:
            result["construction"] = "PU"

    return result


def fetch_products():
    products = []
    page = 1

    while True:
        response = requests.get(
            PRODUCTS_URL,
            headers=HEADERS,
            params={
                "limit": 250,
                "page": page,
            },
            timeout=(10, 60),
        )

        response.raise_for_status()

        page_products = response.json().get("products", [])

        if not page_products:
            break

        products.extend(page_products)

        if len(page_products) < 250:
            break

        page += 1

    return products


def main():
    products = fetch_products()
    now = datetime.now(timezone.utc).isoformat()

    rows = []
    skipped_non_board = 0
    skipped_unavailable = 0
    skipped_parse = 0
    seen = set()

    for product in products:
        title = clean(product.get("title"))
        handle = product.get("handle")
        product_type = clean(product.get("product_type")) or ""
        tags = product.get("tags") or []

        is_board = (
            "surfboard" in product_type.lower()
            or any(str(tag).lower() == "surfboard" for tag in tags)
            or any(str(tag).lower() == "new surfboard" for tag in tags)
        )

        if not is_board:
            skipped_non_board += 1
            continue

        parsed = parse_title(title)

        if not parsed["model"] or not parsed["length"]:
            skipped_parse += 1
            continue

        image_url = first_image(product)

        for variant in product.get("variants") or []:
            if not variant.get("available"):
                skipped_unavailable += 1
                continue

            variant_id = variant.get("id")
            price_amount = money(variant.get("price"))

            dedupe_key = (
                parsed["model"],
                parsed["length"],
                parsed["width"],
                parsed["thickness"],
                str(parsed["volume"]),
                parsed["construction"],
                str(variant_id),
            )

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)

            rows.append({
                "brandName": BRAND_NAME,
                "modelName": parsed["model"],
                "lengthFeetInches": parsed["length"],
                "width": parsed["width"],
                "thickness": parsed["thickness"],
                "volumeLitres": parsed["volume"],
                "construction": parsed["construction"],
                "finSetup": None,
                "tailShape": parsed["tail"],
                "productUrl": build_product_url(handle, variant_id),
                "productImageUrl": image_url,
                "priceAmount": price_amount,
                "priceCurrency": "AUD",
                "stockStatus": "available",
                "isAvailable": True,
                "availabilitySource": AVAILABILITY_SOURCE,
                "regionCode": REGION_CODE,
                "sourceProductId": product.get("id"),
                "sourceVariantId": variant_id,
                "sourceVariantTitle": title,
                "sourceCataloguePath": PRODUCTS_URL,
                "sourceStorefront": SOURCE_STOREFRONT,
                "snapshotUtc": now,
            })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Christenson AU manufacturer availability build complete")
    print(f"Products seen: {len(products)}")
    print(f"Output rows: {len(rows)}")
    print(f"Skipped non board products: {skipped_non_board}")
    print(f"Skipped unavailable variants: {skipped_unavailable}")
    print(f"Skipped parse failures: {skipped_parse}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
