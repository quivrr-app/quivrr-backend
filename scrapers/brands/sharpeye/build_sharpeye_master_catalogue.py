import json
import re
import time
from decimal import Decimal
from pathlib import Path

import requests


BRAND = "Sharp Eye"
BASE_URL = "https://www.sharpeyesurfboards.com.au"

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
    "Accept": "application/json,text/html,*/*",
    "Referer": BASE_URL,
}


def clean(value):
    value = str(value or "")
    value = value.replace("×", "x")
    value = value.replace("\\", "")
    value = value.replace("’", "'")
    value = value.replace("‘", "'")
    value = value.replace("“", '"')
    value = value.replace("”", '"')
    value = value.replace("Â", "")
    value = value.replace("â€“", "-")
    value = value.replace("&quot;", '"')
    return re.sub(r"\s+", " ", value).strip()


def normalise_model_name(title):
    value = clean(title)

    value = re.sub(r"\s*\(E3\s*LITE\)\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*\(E3-LITE\)\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*\(C1\s*LITE\)\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+YTH\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+YOUTH\s*$", "", value, flags=re.IGNORECASE)
    value = clean(value)

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


def detect_fin_setup(value):
    upper = clean(value).upper()

    if "FCS II" in upper or "FCS 2" in upper:
        return "FCS II"

    if "FUTURES" in upper:
        return "Futures"

    return None


def parse_dimension_text(value):
    value = clean(value)
    value = value.replace('"', "")

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

    match = re.search(pattern, value, flags=re.IGNORECASE)

    if not match:
        return None

    return {
        "length_feet_inches": clean(match.group("length").replace(" ", "")),
        "width": clean(match.group("width")),
        "thickness": clean(match.group("thickness")),
        "volume_litres": float(Decimal(match.group("volume"))),
        "is_hv": " HV " in f" {value.upper()} ",
        "raw": value,
    }


def first_image(product):
    images = product.get("images") or []

    if images:
        return images[0].get("src")

    image = product.get("image")

    if isinstance(image, dict):
        return image.get("src")

    return None


def fetch_products():
    products_by_handle = {}

    for collection in COLLECTIONS:
        url = f"{BASE_URL}/collections/{collection}/products.json?limit=250"

        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        response.raise_for_status()

        for product in response.json().get("products", []):
            handle = product.get("handle")

            if handle:
                products_by_handle[handle] = product

        time.sleep(0.25)

    return list(products_by_handle.values())


def extract_dimensions_from_html(product_url):
    response = requests.get(product_url, headers=HEADERS, timeout=(10, 30))
    response.raise_for_status()

    html = response.text
    html = html.replace("\\/", "/")
    html = html.replace("&quot;", '"')
    html = html.replace("Ã—", "x")

    rows = []

    pattern = (
        r'"length_inches"\s*:\s*"(?P<length>[^"]+)"'
        r'.{0,900}?'
        r'"width_inches"\s*:\s*"(?P<width>[^"]+)"'
        r'.{0,900}?'
        r'"thickness_inches"\s*:\s*"(?P<thickness>[^"]+)"'
        r'.{0,900}?'
        r'"volume"\s*:\s*"(?P<volume>[^"]+)"'
        r'.{0,900}?'
        r'"surfboardconstructiontype"\s*:\s*"(?P<construction>[^"]+)"'
        r'.{0,900}?'
        r'"tail"\s*:\s*"(?P<tail>[^"]*)"'
        r'.{0,900}?'
        r'"fin_options"\s*:\s*"(?P<fin_options>[^"]*)"'
    )

    for match in re.finditer(pattern, html, flags=re.IGNORECASE | re.DOTALL):
        length = clean(match.group("length")).replace('"', '')
        width = clean(match.group("width")).replace('"', '')
        thickness = clean(match.group("thickness")).replace('"', '')

        try:
            volume = float(Decimal(clean(match.group("volume"))))
        except Exception:
            continue

        rows.append({
            "length_feet_inches": length,
            "width": width,
            "thickness": thickness,
            "volume_litres": volume,
            "construction": clean(match.group("construction")),
            "fin_setup": normalise_fin_options(match.group("fin_options")),
            "tail_shape": clean(match.group("tail")) or None,
            "raw": f"{length} x {width} x {thickness} {volume} L",
        })

    deduped = []
    seen = set()

    for row in rows:
        key = (
            row["length_feet_inches"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
            row["construction"],
            row["fin_setup"],
            row["tail_shape"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    return deduped


def normalise_fin_options(value):
    value = clean(value)

    if not value:
        return None

    value = value.replace("FCS 2", "FCS II")
    value = value.replace("FCS2", "FCS II")
    value = value.replace("/", " / ")
    value = re.sub(r"\s+", " ", value).strip()

    return value


def add_row(rows, title, tags, product, parsed):
    if not parsed:
        return False

    model_name = normalise_model_name(title)
    product_url = f"{BASE_URL}/products/{product.get('handle')}"

    board_category = "Youth Shortboard" if "YTH" in title.upper() or "YOUTH" in title.upper() else "Shortboard"

    if " HV" in title.upper():
        board_category = "High Volume Shortboard"

    rows.append({
        "brand": BRAND,
        "model_name": model_name,
        "model_family": model_name,
        "board_category": board_category,
        "description": clean(product.get("body_html")),
        "official_product_url": product_url,
        "official_image_url": first_image(product),
        "recommended_wave_range": None,
        "recommended_surfer_weight": None,
        "length_feet_inches": parsed["length_feet_inches"],
        "width": parsed["width"],
        "thickness": parsed["thickness"],
        "volume_litres": parsed["volume_litres"],
        "construction": parsed.get("construction") or detect_construction(title, tags),
        "fin_setup": parsed.get("fin_setup"),
        "tail_shape": parsed.get("tail_shape"),
        "source_product_title": title,
        "source_variant_title": parsed.get("raw"),
        "source": BASE_URL,
    })

    return True


def build_catalogue():
    products = fetch_products()

    rows = []
    failures = []
    product_debug = []

    for product in products:
        title = clean(product.get("title"))
        tags = product.get("tags") or []
        variants = product.get("variants") or []
        product_url = f"{BASE_URL}/products/{product.get('handle')}"

        added = 0

        fallback_dimensions = extract_dimensions_from_html(product_url)

        for dimension in fallback_dimensions:
            if add_row(rows, title, tags, product, dimension):
                added += 1

        product_debug.append({
            "title": title,
            "url": product_url,
            "rows_added": added,
        })

        if added == 0:
            failures.append({
                "model": normalise_model_name(title),
                "title": title,
                "reason": "no dimensions found",
                "product_url": product_url,
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
            row["construction"],
            row["volume_litres"],
            row["length_feet_inches"],
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
        "rows": len(deduped),
        "models": len(set(row["model_name"] for row in deduped)),
        "constructions": sorted(set(row["construction"] for row in deduped)),
        "failures": failures,
        "failure_count": len(failures),
        "product_debug": product_debug,
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

    print("")
    print("Product debug:")

    for item in product_debug:
        print(f" - {item['title']}: {item['rows_added']}")


if __name__ == "__main__":
    build_catalogue()
