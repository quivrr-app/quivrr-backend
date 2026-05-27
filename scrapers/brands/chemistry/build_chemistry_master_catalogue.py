import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests


BRAND_NAME = "Chemistry Surfboards"
REGION_CODE = "AU"
BASE_URL = "https://chemistrysurfboards.com.au"
OUTPUT_DIR = Path("scrapers/brands/chemistry/output")
OUTPUT_FILE = OUTPUT_DIR / "chemistry_master_catalogue_clean.json"
REPORT_FILE = OUTPUT_DIR / "chemistry_master_catalogue_clean_report.json"
RAW_PRODUCTS_FILE = OUTPUT_DIR / "chemistry_au_shopify_products_raw.json"

MODEL_MAP = {
    "b-side": "B-Side",
    "b-side-ex-team": "B-Side",
    "pantera-rosa": "Pantera Rosa",
    "summertime-pt-2": "Summertime Pt 2",
    "the-23": "The 23",
    "the-zen-4": "The Zen 4",
    "the-zen-4-1": "The Zen 4",
    "the-zen-4-stock": "The Zen 4",
    "the-zen-4-6-4": "The Zen 4",
}

BLOCKED_TERMS = [
    "leash",
    "traction",
    "tail pad",
    "deck grip",
    "fin",
    "fins",
    "hat",
    "cap",
    "shirt",
    "tee",
    "wax",
    "gift",
    "sticker",
    "bag",
]


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clean(value):
    if value is None:
        return None

    value = str(value)
    value = value.replace("\u2019", "'").replace("\u2018", "'")
    value = value.replace("\u2032", "'").replace("\u2033", '"')
    value = re.sub(r"\s+", " ", value).strip()

    return value or None


def title_case_slug(value):
    value = clean(value) or ""
    value = value.replace("-", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value.title()


def normalise_length(value):
    value = clean(value) or ""

    match = re.search(r"([4-9])\s*'\s*(\d{1,2})", value)
    if match:
        return f"{match.group(1)}'{int(match.group(2))}"

    match = re.search(r"\b([4-9])\s+(\d{1,2})\b", value)
    if match:
        return f"{match.group(1)}'{int(match.group(2))}"

    match = re.search(r"\b([4-9])(\d{1,2})\b", value)
    if match:
        return f"{match.group(1)}'{int(match.group(2))}"

    return None


def normalise_number_text(value):
    value = clean(value)

    if not value:
        return None

    value = value.replace('"', "")
    value = re.sub(r"\s+", " ", value).strip()

    return value or None


def normalise_volume(value):
    value = clean(value) or ""

    match = re.search(r"(\d{2}(?:\.\d+)?)\s*[lL]\b", value)

    if not match:
        return None

    return float(match.group(1))


def extract_dimensions(value):
    value = clean(value) or ""

    match = re.search(
        r"(?P<length>[4-9]\s*'\s*\d{1,2})\s*\"?\s+"
        r"(?P<width>\d{1,2}(?:\s+\d{1,2}/\d{1,2})?)\s*\"?\s+"
        r"(?P<thickness>\d(?:\s+\d{1,2}/\d{1,2})?)\s*\"?\s+"
        r"(?P<volume>\d{2}(?:\.\d+)?)\s*[lL]",
        value,
        re.IGNORECASE,
    )

    if match:
        return {
            "length": normalise_length(match.group("length")),
            "width": normalise_number_text(match.group("width")),
            "thickness": normalise_number_text(match.group("thickness")),
            "volume_litres": float(match.group("volume")),
        }

    return {
        "length": normalise_length(value),
        "width": None,
        "thickness": None,
        "volume_litres": normalise_volume(value),
    }


def detect_construction(value):
    value = (clean(value) or "").lower()

    if "eps" in value or "epoxy" in value:
        return "EPS"

    if "pu" in value or "poly" in value:
        return "PU"

    return "PU"


def product_image(product):
    images = product.get("images") or []

    if images and images[0].get("src"):
        return images[0].get("src")

    image = product.get("image") or {}

    return image.get("src")


def is_surfboard(product):
    title = clean(product.get("title")) or ""
    handle = clean(product.get("handle")) or ""
    product_type = clean(product.get("product_type")) or ""
    vendor = clean(product.get("vendor")) or ""

    combined = f"{title} {handle} {product_type} {vendor}".lower()

    if any(item in combined for item in BLOCKED_TERMS):
        return False

    return True


def fetch_products():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)"
    })

    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/products.json?limit=250&page={page}"
        response = session.get(url, timeout=60)

        if response.status_code != 200:
            print(f"Feed stopped at page {page}: HTTP {response.status_code}")
            break

        data = response.json()
        page_products = data.get("products") or []

        if not page_products:
            break

        products.extend(page_products)
        page += 1

    return products


def model_name_from_handle(handle):
    handle = clean(handle) or ""
    return MODEL_MAP.get(handle, title_case_slug(handle))


def build_catalogue():
    print("")
    print("=" * 100)
    print("BUILD CHEMISTRY AU MASTER CATALOGUE")
    print("=" * 100)
    print(f"Source: {BASE_URL}/products.json")

    products = fetch_products()

    rows = []
    failures = []
    deduped = {}

    for product in products:
        if not is_surfboard(product):
            continue

        title = clean(product.get("title")) or ""
        handle = clean(product.get("handle")) or ""
        body_html = product.get("body_html")
        variants = product.get("variants") or []

        model_name = model_name_from_handle(handle)
        product_url = f"{BASE_URL}/products/{handle}"

        for variant in variants:
            variant_title = clean(variant.get("title")) or ""
            option1 = clean(variant.get("option1")) or variant_title
            option2 = clean(variant.get("option2")) or ""
            option3 = clean(variant.get("option3")) or ""

            dimensions = extract_dimensions(option1)

            if not dimensions["length"]:
                dimensions = extract_dimensions(f"{variant_title} {title} {handle}")

            if not dimensions["length"]:
                failures.append({
                    "product": title,
                    "variant": variant_title,
                    "reason": "missing length",
                })
                continue

            construction = detect_construction(f"{option2} {option3} {variant_title} {title}")

            key = (
                model_name.lower(),
                dimensions["length"],
                dimensions["width"],
                dimensions["thickness"],
                dimensions["volume_litres"],
                construction,
            )

            existing = deduped.get(key)

            row = {
                "brand": BRAND_NAME,
                "model": model_name,
                "model_name": model_name,
                "model_family": model_name,
                "board_category": "Surfboard",
                "description": None,
                "official_product_url": product_url,
                "official_image_url": product_image(product),
                "recommended_wave_range": None,
                "recommended_surfer_weight": None,
                "length": dimensions["length"],
                "length_feet_inches": dimensions["length"],
                "width": dimensions["width"],
                "thickness": dimensions["thickness"],
                "volume_litres": dimensions["volume_litres"],
                "construction": construction,
                "fin_system": None,
                "fin_setup": None,
                "tail_shape": None,
                "source_product_title": title,
                "source_variant_title": variant_title,
                "source": BASE_URL,
                "source_product_id": product.get("id"),
                "source_variant_id": variant.get("id"),
                "region": REGION_CODE,
                "scraped_at_utc": now_utc(),
                "is_active": True,
            }

            if existing is None:
                deduped[key] = row

    rows = sorted(
        deduped.values(),
        key=lambda row: (
            row["model_name"],
            row["construction"],
            row["length_feet_inches"],
            row["volume_litres"] or 0,
        ),
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    RAW_PRODUCTS_FILE.write_text(
        json.dumps(products, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    models = sorted(set(row["model_name"] for row in rows))
    constructions = sorted(set(row["construction"] for row in rows))

    REPORT_FILE.write_text(
        json.dumps(
            {
                "brand": BRAND_NAME,
                "region": REGION_CODE,
                "source": BASE_URL,
                "source_url": f"{BASE_URL}/products.json",
                "products_found": len(products),
                "catalogue_rows": len(rows),
                "models": len(models),
                "model_names": models,
                "constructions": constructions,
                "failures": failures,
                "failure_count": len(failures),
                "output_file": str(OUTPUT_FILE),
                "raw_products_file": str(RAW_PRODUCTS_FILE),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("=" * 100)
    print("CHEMISTRY AU COMPLETE")
    print("=" * 100)
    print("Products found:", len(products))
    print("Catalogue rows:", len(rows))
    print("Models:", len(models))
    print("Constructions:", constructions)
    print("Failures:", len(failures))
    print("Output:", OUTPUT_FILE)
    print("Report:", REPORT_FILE)


if __name__ == "__main__":
    build_catalogue()
