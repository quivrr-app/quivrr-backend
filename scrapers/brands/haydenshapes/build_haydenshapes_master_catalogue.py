import json
import re
import time
from decimal import Decimal
from pathlib import Path

import requests


BRAND = "Haydenshapes"
BASE_URL = "https://au.haydenshapes.com"
COLLECTION = "surfboard-models"

OUTPUT_FILE = Path("scrapers/brands/haydenshapes/output/haydenshapes_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/haydenshapes/output/haydenshapes_master_catalogue_clean_report.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}

SKIP_TERMS = [
    "softboard",
    "soft board",
    "gift card",
    "tee",
    "shirt",
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
        "â€™": "'",
        "â€²": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "″": '"',
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
    }

    for old_value, new_value in replacements.items():
        value = value.replace(old_value, new_value)

    return re.sub(r"\s+", " ", value).strip()


def normalise_model_name(title):
    value = clean(title)

    suffixes = [
        "FutureFlex",
        "Futureflex",
        "PU",
        "EPS",
        "PE",
        "Softboard",
        "Soft Board",
        "Cobalt Blue",
    ]

    for suffix in suffixes:
        value = re.sub(
            rf"\s+{re.escape(suffix)}$",
            "",
            value,
            flags=re.IGNORECASE,
        )

    value = re.sub(r"\s+-\s+Single Fin$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def detect_construction(title, variant_title, product_tags):
    combined = f"{title} {variant_title} {' '.join(product_tags or [])}".upper()

    if "FUTUREFLEX" in combined or "FUTURE FLEX" in combined:
        return "FutureFlex"

    if "SOFTBOARD" in combined or "SOFT BOARD" in combined:
        return "Softboard"

    if "EPS" in combined:
        return "EPS"

    if "PU" in combined:
        return "PU"

    if "PE" in combined:
        return "PE"

    return "FutureFlex"


def detect_fin_setup(title, variant_title):
    combined = f"{title} {variant_title}".upper()

    if "FCSII" in combined or "FCS II" in combined or "FCS 2" in combined:
        return "FCS II"

    if "FUTURES" in combined:
        return "Futures"

    if "SINGLE" in combined:
        return "Single"

    if "TWIN" in combined:
        return "Twin"

    return None


def parse_dimension_text(text_value):
    text_value = clean(text_value)
    text_value = text_value.replace("×", "x")
    text_value = text_value.replace('"', "")
    text_value = text_value.replace("”", "")
    text_value = text_value.replace("″", "")

    patterns = [
        r"(?P<length>\d+'\s*\d{1,2})\s*x\s*(?P<width>\d+(?:\s+\d+/\d+)?|\d+\.\d+)\s*x\s*(?P<thickness>\d+(?:\s+\d+/\d+)?|\d+\.\d+)\s*[-/x ]+\s*(?P<volume>\d+(?:\.\d+)?)\s*l",
        r"(?P<length>\d+'\s*\d{1,2}).*?(?P<width>\d+(?:\s+\d+/\d+)?|\d+\.\d+).*?(?P<thickness>\d+(?:\s+\d+/\d+)?|\d+\.\d+).*?(?P<volume>\d+(?:\.\d+)?)\s*l",
    ]

    for pattern in patterns:
        match = re.search(pattern, text_value, flags=re.IGNORECASE)

        if match:
            return {
                "length": clean(match.group("length").replace(" ", "")),
                "width": clean(match.group("width")),
                "thickness": clean(match.group("thickness")),
                "volume_litres": Decimal(match.group("volume")),
            }

    length_match = re.search(r"(?P<length>\d+'\s*\d{1,2})", text_value)
    volume_match = re.search(r"(?P<volume>\d+(?:\.\d+)?)\s*l", text_value, flags=re.IGNORECASE)

    return {
        "length": clean(length_match.group("length").replace(" ", "")) if length_match else None,
        "width": None,
        "thickness": None,
        "volume_litres": Decimal(volume_match.group("volume")) if volume_match else None,
    }


def parse_decimal(value):
    if value in [None, ""]:
        return None

    try:
        return Decimal(str(value).replace(",", "").strip())
    except Exception:
        return None


def first_image(product):
    images = product.get("images") or []

    if images:
        return images[0].get("src")

    image = product.get("image")

    if isinstance(image, dict):
        return image.get("src")

    return None


def should_skip_product(product):
    title = clean(product.get("title")).lower()
    product_type = clean(product.get("product_type")).lower()
    tags = " ".join(product.get("tags") or []).lower()

    combined = f"{title} {product_type} {tags}"

    return any(term in combined for term in SKIP_TERMS)


def fetch_products():
    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/collections/{COLLECTION}/products.json?limit=250&page={page}"
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        response.raise_for_status()

        batch = response.json().get("products", [])

        if not batch:
            break

        products.extend(batch)

        if len(batch) < 250:
            break

        page += 1
        time.sleep(0.3)

    return products


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
        product_url = f"{BASE_URL}/products/{product.get('handle')}"
        image_url = first_image(product)

        variants = product.get("variants") or []

        if not variants:
            failures.append({
                "title": title,
                "reason": "no variants",
                "product_url": product_url,
            })
            continue

        for variant in variants:
            variant_title = clean(variant.get("title"))

            if not variant_title or variant_title.lower() == "default title":
                source_text = title
            else:
                source_text = f"{title} {variant_title}"

            dimensions = parse_dimension_text(source_text)

            if not dimensions["length"]:
                failures.append({
                    "model": model_name,
                    "title": title,
                    "variant_title": variant_title,
                    "reason": "could not parse length",
                    "product_url": product_url,
                })
                continue

            construction = detect_construction(title, variant_title, tags)

            if construction.lower() == "softboard":
                skipped += 1
                continue

            rows.append({
                "brand": BRAND,
                "model_name": model_name,
                "model_family": model_name,
                "board_category": None,
                "description": clean(product.get("body_html")),
                "official_product_url": product_url,
                "official_image_url": image_url,
                "recommended_wave_range": None,
                "recommended_surfer_weight": None,
                "length_feet_inches": dimensions["length"],
                "width": dimensions["width"],
                "thickness": dimensions["thickness"],
                "volume_litres": float(dimensions["volume_litres"]) if dimensions["volume_litres"] is not None else None,
                "construction": construction,
                "fin_setup": detect_fin_setup(title, variant_title),
                "tail_shape": None,
                "source_product_title": title,
                "source_variant_title": variant_title,
                "source": BASE_URL,
            })

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
        "collection": COLLECTION,
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
    print("HAYDENSHAPES COMPLETE")
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
