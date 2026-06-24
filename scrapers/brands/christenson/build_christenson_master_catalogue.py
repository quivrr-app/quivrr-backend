import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BRAND_NAME = "Christenson"
REGION_CODE = "AU"
BASE_URL = "https://christensonsurfboards.com.au"
SOURCE_URL = "https://christensonsurfboards.com.au/collections/surfboards/products.json?limit=250"

OUTPUT_DIR = Path("scrapers/brands/christenson/output")
OUTPUT_FILE = OUTPUT_DIR / "christenson_master_catalogue_clean.json"
REPORT_FILE = OUTPUT_DIR / "christenson_master_catalogue_clean_report.json"
RAW_PRODUCTS_FILE = OUTPUT_DIR / "christenson_au_shopify_products_raw.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}

TITLE_PATTERN = re.compile(
    r"^(?P<model>.*?)\s+"
    r"(?P<length>\d+'\d{1,2})\"\s*[xX]\s*"
    r"(?P<width>\d+(?:\s+\d+/\d+|\.\d+|/\d+)?)\"\s*[xX]\s*"
    r"(?P<thickness>\d+(?:\s+\d+/\d+|\.\d+|/\d+)?)\""
    r"(?:\s*-\s*(?P<volume>\d+(?:\.\d+)?)L)?"
    r"(?:,\s*(?P<tail>[^,]+))?"
    r"(?:,\s*(?P<fins>[^,]+?)\s+Fin Boxes)?"
    r"(?:,\s*(?P<construction>PU|PE|EPS|Epoxy|Carbon|Dark Arts))?"
    r"(?:\s*-\s*ID:(?P<source_id>\d+))?",
    re.I,
)

SKIP_PRODUCT_TYPES = {
    "fins",
    "tees - short sleeve",
    "custom board",
    "accessories",
    "leashes",
    "apparel",
    "hats",
    "stickers",
    "skateboards",
}

SKIP_TITLE_TERMS = [
    "tee",
    "hat",
    "shirt",
    "sticker",
    "leash",
    "custom order",
]


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(value):
    if not value:
        return None

    soup = BeautifulSoup(value, "html.parser")
    return clean(unescape(soup.get_text(" ", strip=True))) or None


def extract_model_type(product):
    body = product.get("body_html") or ""
    soup = BeautifulSoup(body, "html.parser")
    text = clean(unescape(soup.get_text(" ", strip=True)))

    match = re.search(r"Surfboard Model Type:\s*([^\n\r]+?)(?:\s{2,}|Fins:|$)", text, re.I)

    if not match:
        return None

    value = clean(match.group(1))

    if not value:
        return None

    lowered = value.lower()

    if "fish" in lowered:
        return "Fish"

    if "hybrid" in lowered:
        return "Hybrid"

    if "long" in lowered:
        return "Longboard"

    if "mid" in lowered:
        return "Mid Length"

    if "gun" in lowered or "step" in lowered:
        return "Step Up"

    return value


def extract_description(product):
    body = product.get("body_html")

    if not body:
        return None

    soup = BeautifulSoup(body, "html.parser")

    for br in soup.find_all("br"):
        br.replace_with("\n")

    text = unescape(soup.get_text("\n", strip=True))

    lines = []

    skip_prefixes = (
        "surfboard model:",
        "surfboard id:",
        "surfboard model type:",
        "fins:",
    )

    skip_next = False

    for line in text.splitlines():
        line = clean(line)

        if not line:
            continue

        if skip_next:
            skip_next = False
            continue

        lowered = line.lower()

        if any(lowered.startswith(prefix) for prefix in skip_prefixes):
            skip_next = True
            continue

        lines.append(line)

    description = clean(" ".join(lines))

    return description or None


def fetch_products():
    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=(10, 60),
    )
    response.raise_for_status()

    products = response.json().get("products", [])

    RAW_PRODUCTS_FILE.write_text(
        json.dumps(products, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return products


def normalise_model(value):
    value = clean(value)

    replacements = {
        "Op3": "OP3",
        "C Bucket": "C-Bucket",
        "Long Phish Ii": "Long Phish II",
    }

    value = value.replace(" -", " ")
    value = re.sub(r"\s+", " ", value).strip()
    value = value.title()

    for old, new in replacements.items():
        value = value.replace(old, new)

    return clean(value)


def normalise_fin(value):
    value = clean(value)

    if not value:
        return None

    lowered = value.lower()

    if "fcs" in lowered:
        return "FCS II"

    if "future" in lowered:
        return "Futures"

    return value


def normalise_construction(value):
    value = clean(value)

    if not value:
        return "PU"

    lowered = value.lower()

    if lowered == "pu":
        return "PU"

    if lowered == "pe":
        return "PE"

    if "eps" in lowered:
        return "EPS"

    if "epoxy" in lowered:
        return "Epoxy"

    if "carbon" in lowered:
        return "Carbon"

    if "dark arts" in lowered:
        return "Dark Arts"

    return value


def is_surfboard(product):
    title = clean(product.get("title")).lower()
    product_type = clean(product.get("product_type")).lower()
    vendor = clean(product.get("vendor")).lower()

    if product_type in SKIP_PRODUCT_TYPES:
        return False

    if any(term in title for term in SKIP_TITLE_TERMS):
        return False

    if vendor not in ["chris christenson", "christenson surfboards australia", "christenson"]:
        return False

    return bool(TITLE_PATTERN.search(product.get("title") or ""))


def get_image(product):
    images = product.get("images") or []

    if images and images[0].get("src"):
        return images[0].get("src")

    image = product.get("image") or {}
    return image.get("src")


def build_catalogue():
    print("")
    print("=" * 100)
    print("BUILD CHRISTENSON AU MASTER CATALOGUE")
    print("=" * 100)
    print("Source:", SOURCE_URL)

    products = fetch_products()

    rows = []
    failures = []

    for product in products:
        title = clean(product.get("title"))
        handle = clean(product.get("handle"))

        if not is_surfboard(product):
            continue

        match = TITLE_PATTERN.search(title)

        if not match:
            failures.append({
                "title": title,
                "reason": "title did not match dimension pattern",
            })
            continue

        volume_raw = match.group("volume")

        if not volume_raw:
            failures.append({
                "title": title,
                "reason": "missing volume",
            })
            continue

        volume = float(volume_raw)
        description = extract_description(product)
        model_type = extract_model_type(product)

        if volume <= 0:
            failures.append({
                "title": title,
                "reason": "zero volume ignored",
            })
            continue

        model = normalise_model(match.group("model"))
        construction = normalise_construction(match.group("construction"))
        fin_setup = normalise_fin(match.group("fins"))
        tail_shape = clean(match.group("tail"))
        product_url = urljoin(BASE_URL.rstrip("/") + "/", f"products/{handle}")

        rows.append({
            "brand": BRAND_NAME,
            "model_name": model,
            "model_family": model,
            "board_category": christenson_category_from_type(model_type),
            "description": description,
            "official_product_url": product_url,
            "official_image_url": get_image(product),
            "recommended_wave_range": None,
            "recommended_surfer_weight": None,
            "length_feet_inches": clean(match.group("length")),
            "width": clean(match.group("width")),
            "thickness": clean(match.group("thickness")),
            "volume_litres": volume,
            "construction": construction,
            "fin_setup": fin_setup,
            "tail_shape": tail_shape,
            "source_product_title": title,
            "source_variant_title": title,
            "source": BASE_URL,
            "source_product_id": product.get("id"),
            "source_handle": handle,
            "source_board_id": match.group("source_id"),
            "region": REGION_CODE,
            "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        })

    deduped_by_key = {}

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

        if key not in deduped_by_key:
            deduped_by_key[key] = row

    deduped = sorted(
        deduped_by_key.values(),
        key=lambda row: (
            row["model_name"].lower(),
            row["construction"],
            row["length_feet_inches"],
            row["fin_setup"] or "",
        ),
    )

    OUTPUT_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    RAW_PRODUCTS_FILE.write_text(
        json.dumps(products, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    models = sorted(set(row["model_name"] for row in deduped))
    constructions = sorted(set(row["construction"] for row in deduped))
    fin_setups = sorted(set(row["fin_setup"] for row in deduped if row["fin_setup"]))

    REPORT_FILE.write_text(
        json.dumps(
            {
                "brand": BRAND_NAME,
                "region": REGION_CODE,
                "source": BASE_URL,
                "source_url": SOURCE_URL,
                "products_found": len(products),
                "catalogue_rows": len(deduped),
                "models": len(models),
                "model_names": models,
                "constructions": constructions,
                "fin_setups": fin_setups,
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
    print("CHRISTENSON AU COMPLETE")
    print("=" * 100)
    print("Products found:", len(products))
    print("Catalogue rows:", len(deduped))
    print("Models:", len(models))
    print("Constructions:", constructions)
    print("Fin setups:", fin_setups)
    print("Failures:", len(failures))
    print("Output:", OUTPUT_FILE)
    print("Report:", REPORT_FILE)


if __name__ == "__main__":
    build_catalogue()
