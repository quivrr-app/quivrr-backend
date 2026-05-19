from pathlib import Path

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")
path.parent.mkdir(parents=True, exist_ok=True)

path.write_text(r'''
import json
import re
import time
from decimal import Decimal
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BRAND = "Sharp Eye"
BASE_URL = "https://sharpeyesurfboards.com"

COLLECTIONS = [
    "performance-range",
    "pro-range",
    "hv-range",
    "alternate-range",
    "youth-range",
]

OUTPUT_FILE = Path("scrapers/brands/sharpeye/output/sharpeye_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/sharpeye/output/sharpeye_master_catalogue_clean_report.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Referer": BASE_URL,
}

SKIP_TERMS = [
    "accessory",
    "apparel",
    "shirt",
    "tee",
    "hat",
    "cap",
    "traction",
    "tail pad",
    "deck grip",
    "wax",
    "bag",
    "cover",
]


def clean(value):
    value = str(value or "")

    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "×": "x",
        "â€“": "-",
        "Â": "",
    }

    for old_value, new_value in replacements.items():
        value = value.replace(old_value, new_value)

    return re.sub(r"\s+", " ", value).strip()


def normalise_model_name(title):
    value = clean(title)

    suffix_patterns = [
        r"\s*\(E3\s*LITE\)\s*$",
        r"\s*\(E3-LITE\)\s*$",
        r"\s*\(C1\s*LITE\)\s*$",
        r"\s+YTH\s*$",
        r"\s+YOUTH\s*$",
    ]

    for pattern in suffix_patterns:
        value = re.sub(pattern, "", value, flags=re.IGNORECASE)

    value = re.sub(r"\s+", " ", value).strip()

    aliases = {
        "#77": "#77",
        "CHEAT CODE": "Cheat Code",
        "DISCO II": "Disco II",
        "DISCO INFERNO": "Disco Inferno",
        "DISCO": "Disco",
        "FILE FIFTY": "File Fifty",
        "HOLY TOLEDO": "Holy Toledo",
        "HT2.5": "HT2.5",
        "HT2": "HT2",
        "INFERNO 72": "Inferno 72",
        "INFERNO FT": "Inferno FT",
        "MAGURO": "Maguro",
        "MIDGICIAN": "Midgician",
        "MODERN 2.5": "Modern 2.5",
        "MODERN 2": "Modern 2",
        "OKAY": "Okay",
        "RADAR": "Radar",
        "SB-1": "SB-1",
        "STORMS": "Storms",
        "SYNERGY": "Synergy",
        "TWIN TURBO": "Twin Turbo",
        "ZIPPER": "Zipper",
    }

    upper = value.upper()

    for source, target in aliases.items():
        if upper.startswith(source):
            return target

    return value.title()


def detect_construction(title, tags):
    combined = f"{title} {' '.join(tags or [])}".upper()

    if "C1 LITE" in combined or "C1-LITE" in combined or "C1 CARBON" in combined or "C1-CARBON" in combined:
        return "C1 Lite"

    if "E3 LITE" in combined or "E3-LITE" in combined or "E3-EPS" in combined or "E3 EPS" in combined:
        return "E3 Lite"

    return "PU"


def detect_fin_setup(text_value):
    upper = clean(text_value).upper()

    if "FCS 2" in upper or "FCSII" in upper or "FCS II" in upper:
        return "FCS II"

    if "FUTURES" in upper:
        return "Futures"

    if "TWIN" in upper:
        return "Twin"

    return None


def parse_dimensions(text_value):
    text_value = clean(text_value)
    text_value = text_value.replace('"', "")
    text_value = text_value.replace("”", "")
    text_value = text_value.replace("″", "")
    text_value = text_value.replace("×", "x")

    pattern = (
        r"(?P<length>\d+'\s*\d{1,2})"
        r"(?:\s*HV)?"
        r"\s*x\s*"
        r"(?P<width>\d+(?:\.\d+)?)"
        r"\s*x\s*"
        r"(?P<thickness>\d+(?:\.\d+)?)"
        r"\s*(?:x\s*)?"
        r"(?P<volume>\d+(?:\.\d+)?)\s*L"
    )

    match = re.search(pattern, text_value, flags=re.IGNORECASE)

    if not match:
        return {
            "length": None,
            "width": None,
            "thickness": None,
            "volume_litres": None,
            "is_hv": " HV " in f" {text_value.upper()} ",
        }

    return {
        "length": clean(match.group("length").replace(" ", "")),
        "width": clean(match.group("width")),
        "thickness": clean(match.group("thickness")),
        "volume_litres": Decimal(match.group("volume")),
        "is_hv": " HV " in f" {text_value.upper()} ",
    }


def first_image(product):
    images = product.get("images") or []

    if images:
        return images[0].get("src")

    image = product.get("image")

    if isinstance(image, dict):
        return image.get("src")

    return None


def should_skip_product(product):
    combined = " ".join([
        clean(product.get("title")),
        clean(product.get("product_type")),
        " ".join(product.get("tags") or []),
    ]).lower()

    return any(term in combined for term in SKIP_TERMS)


def extract_dimensions_from_html(product_url):
    response = requests.get(
        product_url,
        headers=HEADERS,
        timeout=(10, 30),
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    candidates = []

    for element in soup.select(".surfboard_product_item--title"):
        value = clean(element.get_text(" ", strip=True))

        if re.search(r"\d+'\s*\d{1,2}", value) and "L" in value.upper():
            candidates.append(value)

    if not candidates:
        visible_text = soup.get_text(" ", strip=True)
        visible_text = clean(visible_text)

        candidates = re.findall(
            r"\d+'\s*\d{1,2}\"?\s*x\s*\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s*L",
            visible_text,
            flags=re.IGNORECASE,
        )

    cleaned = []

    for candidate in candidates:
        value = clean(candidate).replace("×", "x")

        if parse_dimensions(value)["length"] and value not in cleaned:
            cleaned.append(value)

    return cleaned


def fetch_products():
    products_by_handle = {}

    for collection in COLLECTIONS:
        url = f"{BASE_URL}/collections/{collection}/products.json?limit=250"

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=(10, 30),
        )

        response.raise_for_status()

        for product in response.json().get("products", []):
            handle = product.get("handle")

            if handle:
                products_by_handle[handle] = product

        time.sleep(0.3)

    return list(products_by_handle.values())


def append_row(rows, product, title, model_name, construction, product_url, image_url, description, source_variant_title, dimensions):
    board_category = "Youth Shortboard" if "YTH" in title.upper() or "YOUTH" in title.upper() else "Shortboard"

    if dimensions.get("is_hv"):
        board_category = "High Volume Shortboard"

    rows.append({
        "brand": BRAND,
        "model_name": model_name,
        "model_family": model_name,
        "board_category": board_category,
        "description": description,
        "official_product_url": product_url,
        "official_image_url": image_url,
        "recommended_wave_range": None,
        "recommended_surfer_weight": None,
        "length_feet_inches": dimensions["length"],
        "width": dimensions["width"],
        "thickness": dimensions["thickness"],
        "volume_litres": float(dimensions["volume_litres"]) if dimensions["volume_litres"] is not None else None,
        "construction": construction,
        "fin_setup": detect_fin_setup(source_variant_title),
        "tail_shape": None,
        "source_product_title": title,
        "source_variant_title": source_variant_title,
        "source": BASE_URL,
    })


def build_catalogue():
    products = fetch_products()

    rows = []
    failures = []
    skipped = 0

    for product in products:
        title = clean(product.get("title"))
        tags = product.get("tags") or []

        if should_skip_product(product):
            skipped += 1
            continue

        model_name = normalise_model_name(title)
        construction = detect_construction(title, tags)
        product_url = f"{BASE_URL}/products/{product.get('handle')}"
        image_url = first_image(product)
        description = clean(product.get("body_html"))

        variants = product.get("variants") or []

        for variant in variants:
            variant_title = clean(variant.get("title"))

            if not variant_title or variant_title.lower() == "default title":
                fallback_dimensions = extract_dimensions_from_html(product_url)

                if not fallback_dimensions:
                    failures.append({
                        "model": model_name,
                        "title": title,
                        "variant_title": variant_title,
                        "reason": "default title variant has no dimensions",
                        "product_url": product_url,
                    })
                    continue

                for fallback_variant in fallback_dimensions:
                    dimensions = parse_dimensions(fallback_variant)

                    if dimensions["length"]:
                        append_row(
                            rows,
                            product,
                            title,
                            model_name,
                            construction,
                            product_url,
                            image_url,
                            description,
                            fallback_variant,
                            dimensions,
                        )

                continue

            dimensions = parse_dimensions(variant_title)

            if not dimensions["length"]:
                failures.append({
                    "model": model_name,
                    "title": title,
                    "variant_title": variant_title,
                    "reason": "could not parse dimensions",
                    "product_url": product_url,
                })
                continue

            append_row(
                rows,
                product,
                title,
                model_name,
                construction,
                product_url,
                image_url,
                description,
                variant_title,
                dimensions,
            )

    seen = set()
    deduped = []

    for row in rows:
        key = (
            row["model_name"].lower(),
            row["length_feet_inches"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
            row["construction"],
            row["fin_setup"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    deduped.sort(
        key=lambda row: (
            row["model_name"],
            row["construction"] or "",
            row["volume_litres"] or 0,
            row["length_feet_inches"] or "",
        )
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report = {
        "brand": BRAND,
        "source": BASE_URL,
        "collections": COLLECTIONS,
        "products_seen": len(products),
        "products_skipped": skipped,
        "rows": len(deduped),
        "models": len(set(row["model_name"] for row in deduped)),
        "constructions": sorted(set(row["construction"] for row in deduped if row["construction"])),
        "failures": failures,
        "failure_count": len(failures),
        "output_file": str(OUTPUT_FILE),
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("=" * 100)
    print("SHARP EYE COMPLETE")
    print("=" * 100)
    print("Products seen:", len(products))
    print("Rows:", len(deduped))
    print("Models:", report["models"])
    print("Constructions:", report["constructions"])
    print("Failures:", len(failures))
    print("Output:", OUTPUT_FILE)
    print("Report:", REPORT_FILE)


if __name__ == "__main__":
    build_catalogue()
'''.strip() + "\n", encoding="utf-8")

print("Rebuilt Sharp Eye builder cleanly")
