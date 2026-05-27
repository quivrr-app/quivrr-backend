import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BRAND_NAME = "Firewire"
BASE_URL = "https://aus.firewiresurfboards.com"
COLLECTION = "prestige-surfboards"

OUTPUT_DIR = Path("scrapers/brands/firewire/output")
CATALOGUE_FILE = OUTPUT_DIR / "firewire_master_catalogue_clean.json"
REPORT_FILE = OUTPUT_DIR / "firewire_master_catalogue_clean_report.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(value):
    if not value:
        return None

    soup = BeautifulSoup(value, "html.parser")
    return clean(soup.get_text(" ", strip=True))


def normalise_model(value):
    value = clean(value)
    value = re.sub(r"\s+2025$", "", value, flags=re.I)
    value = re.sub(r"\s+2026$", "", value, flags=re.I)
    return value


def normalise_measure(value):
    value = clean(value)
    value = value.replace('"', "")
    value = value.replace("L", "")
    return clean(value)


def normalise_length(value):
    value = clean(value)
    value = value.replace('"', "")
    value = value.replace(" ", "")

    if value.endswith("'"):
        value = value + "0"

    return value


def normalise_construction(value):
    value = clean(value)

    if not value:
        return None

    upper = value.upper()

    if "G-FLEX" in upper:
        return "G-Flex"

    if "I-BOLIC 2.0" in upper:
        return "I-Bolic 2.0"

    if "I-BOLIC" in upper and "VOLCANIC" in upper:
        return "I-Bolic Volcanic"

    if "I-BOLIC" in upper:
        return "I-Bolic"

    if "HELIUM" in upper:
        return "Helium"

    if "VOLCANIC" in upper:
        return "Volcanic"

    if "PROFLEX" in upper:
        return "Proflex"

    if "TIMBERTEK" in upper:
        return "TimberTek"

    if "THUNDERBOLT" in upper:
        return "Thunderbolt"

    return value


def should_skip_product(product):
    title = clean(product.get("title"))
    handle = clean(product.get("handle"))
    text = f"{title} {handle}".lower()

    skip_terms = [
        "fin set",
        "traction",
        "pad",
        "leash",
        "shirt",
        "tee",
        "hat",
        "cap",
        "bag",
        "wax",
        "tail pad",
        "gift card",
    ]

    return any(term in text for term in skip_terms)


def fetch_products():
    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/collections/{COLLECTION}/products.json?limit=250&page={page}"
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        response.raise_for_status()

        data = response.json()
        page_products = data.get("products", [])

        if not page_products:
            break

        products.extend(page_products)

        if len(page_products) < 250:
            break

        page += 1

    return products


def get_product_image(product):
    images = product.get("images") or []

    if images:
        return images[0].get("src")

    image = product.get("image") or {}

    if isinstance(image, dict):
        return image.get("src")

    return None


def extract_dimensions(dimension_text):
    text = clean(dimension_text)

    text = text.replace("×", "x")
    text = text.replace(" X ", " x ")
    text = text.replace("”", '"')
    text = text.replace("″", '"')
    text = text.replace("6'x", "6'0\" x")
    text = text.replace("5'x", "5'0\" x")
    text = text.replace("7'x", "7'0\" x")
    text = text.replace("8'x", "8'0\" x")

    text = re.sub(r"\s+", " ", text).strip()

    length_match = re.search(
        r"\d+'\s*\d*\"?",
        text,
        re.I,
    )

    volume_match = re.search(
        r"(\d+(?:\.\d+)?)\s*L\b",
        text,
        re.I,
    )

    if not length_match or not volume_match:
        return None

    length = length_match.group(0)

    middle = text[length_match.end():volume_match.start()]
    middle = middle.replace("L", "")
    middle = middle.replace("l", "")

    middle = re.sub(r"^\s*x\s*", "", middle, flags=re.I)
    middle = re.sub(r"\s*x\s*$", "", middle, flags=re.I)

    parts = [
        clean(part)
        for part in re.split(r"\s+x\s+", middle, flags=re.I)
        if clean(part)
    ]

    if len(parts) < 2:
        return None

    width = parts[0]
    thickness = parts[1]
    volume = float(volume_match.group(1))

    return {
        "length": normalise_length(length),
        "width": normalise_measure(width),
        "thickness": normalise_measure(thickness),
        "volume_litres": volume,
    }


def parse_variant(product, variant):
    variant_title = clean(variant.get("title"))
    parts = [clean(part) for part in variant_title.split(" / ")]

    if len(parts) < 2:
        return None, "variant title does not contain enough parts"

    dimension_part = parts[-1]
    construction_candidates = parts[:-1]

    construction_part = None

    for part in construction_candidates:
        upper = part.upper()

        if any(token in upper for token in [
            "HELIUM",
            "I-BOLIC",
            "VOLCANIC",
            "PROFLEX",
            "G-FLEX",
            "TIMBERTEK",
            "THUNDERBOLT",
        ]):
            construction_part = part
            break

    if not construction_part and len(parts) >= 3:
        construction_part = parts[-2]

    dimensions = extract_dimensions(dimension_part)

    if not dimensions:
        return None, "dimension pattern did not match"

    return {
        **dimensions,
        "construction": normalise_construction(construction_part),
        "variant_title": variant_title,
    }, None


def build_catalogue():
    products = fetch_products()

    rows = []
    failures = []

    print("")
    print("=" * 80)
    print("FIREWIRE MASTER CATALOGUE BUILD")
    print("=" * 80)
    print("Products seen:", len(products))

    for product in products:
        if should_skip_product(product):
            continue

        title = clean(product.get("title"))
        model = normalise_model(title)
        description = strip_html(product.get("body_html"))
        product_url = f"{BASE_URL}/products/{product.get('handle')}"
        image_url = get_product_image(product)

        variants = product.get("variants") or []

        for variant in variants:
            parsed, failure_reason = parse_variant(product, variant)

            if not parsed:
                failures.append({
                    "model": model,
                    "title": title,
                    "variant_title": clean(variant.get("title")),
                    "reason": failure_reason,
                    "product_url": product_url,
                })
                continue

            rows.append({
                "brand": BRAND_NAME,
                "model": model,
                "model_family": model,
                "board_category": "Surfboard",
                "description": description,
                "length": parsed["length"],
                "width": parsed["width"],
                "thickness": parsed["thickness"],
                "volume_litres": parsed["volume_litres"],
                "construction": parsed["construction"],
                "fin_system": None,
                "tail_shape": None,
                "official_product_url": product_url,
                "official_image_url": image_url,
                "source": "firewiresurfboards.com/prestige-surfboards",
                "source_product_id": product.get("id"),
                "source_variant_id": variant.get("id"),
                "source_product_handle": product.get("handle"),
                "source_title": title,
                "source_variant_title": parsed["variant_title"],
                "is_active": True,
            })

    seen = set()
    deduped = []

    for row in rows:
        key = (
            row["model"],
            row["length"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
            row["construction"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    CATALOGUE_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    models = sorted(set(row["model"] for row in deduped))
    constructions = sorted(set(row["construction"] for row in deduped if row.get("construction")))

    REPORT_FILE.write_text(
        json.dumps(
            {
                "brand": BRAND_NAME,
                "source": BASE_URL,
                "collection": COLLECTION,
                "products_seen": len(products),
                "rows": len(deduped),
                "models": len(models),
                "constructions": constructions,
                "failures": failures[:200],
                "failure_count": len(failures),
                "output_file": str(CATALOGUE_FILE),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("=" * 80)
    print("FIREWIRE COMPLETE")
    print("=" * 80)
    print("Products seen:", len(products))
    print("Models:", len(models))
    print("Rows:", len(deduped))
    print("Constructions:", constructions)
    print("Failures:", len(failures))
    print("Output:", CATALOGUE_FILE)
    print("Report:", REPORT_FILE)


if __name__ == "__main__":
    build_catalogue()
