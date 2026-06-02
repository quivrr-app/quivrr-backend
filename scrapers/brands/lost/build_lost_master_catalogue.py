import json
import re
from html import unescape
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BRAND_NAME = "Lost"
REGION_CODE = "AU"
SOURCE_NAME = "lostsurfboards.com.au"
SITE_BASE_URL = "https://lostsurfboards.com.au"
SHOP_ALL_URL = "https://lostsurfboards.com.au/collections/shop-all/products.json?limit=250"

OUTPUT_DIR = Path("scrapers/brands/lost/output")
CATALOGUE_FILE = OUTPUT_DIR / "lost_master_catalogue_clean.json"
REPORT_FILE = OUTPUT_DIR / "lost_master_catalogue_clean_report.json"
RAW_PRODUCTS_FILE = OUTPUT_DIR / "lost_au_shopify_products_raw.json"
VARIANT_SUMMARY_FILE = OUTPUT_DIR / "lost_au_variant_summary.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}

SKIP_PRODUCT_TERMS = [
    "fin", "fins", "leash", "pad", "tail pad", "traction",
    "wax", "bag", "cover", "hat", "tee", "shirt", "hoodie", "sticker",
]


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(value):
    if not value:
        return None
    soup = BeautifulSoup(value, "html.parser")
    return clean(unescape(soup.get_text(" ", strip=True))) or None


def fetch_json(url):
    response = requests.get(url, headers=HEADERS, timeout=(10, 60))
    response.raise_for_status()
    return response.json()


def is_surfboard_product(product):
    title = clean(product.get("title")).lower()
    product_type = clean(product.get("product_type")).lower()
    vendor = clean(product.get("vendor")).lower()
    tags = [clean(tag).lower() for tag in product.get("tags", [])]
    tag_text = " ".join(tags)

    if product_type != "surfboards":
        return False

    if vendor not in ["lost", "lib tech"]:
        return False

    if any(term in title for term in SKIP_PRODUCT_TERMS):
        return False

    return (
        "level 2:surfboards" in tag_text
        or "surfboards" in tags
        or product_type == "surfboards"
    )


def infer_construction(product):
    title = clean(product.get("title")).lower()
    vendor = clean(product.get("vendor")).lower()
    tags = [clean(tag).lower() for tag in product.get("tags", [])]
    tag_text = " ".join(tags)

    if vendor == "lib tech" or "lib tech" in title or "lib tech" in tag_text:
        return "Lib Tech"

    if "black sheep" in title or "blacksheep" in title or "black sheep" in tag_text or "blacksheep" in tag_text:
        return "Black Sheep"

    if "light speed" in title or "lightspeed" in title or "light speed" in tag_text or "lightspeed" in tag_text:
        return "LightSpeed"

    if "stringered epoxy" in title or " eps" in title or title.endswith("eps"):
        return "Epoxy"

    return "PU"


def normalise_model_name(value):
    value = clean(value)

    replacements = [
        (r"\bLib\s*Tech\s*[-:]\s*Lost\b", ""),
        (r"\bLib\s*Tech\b", ""),
        (r"\bLost\b", ""),
        (r"\bSurfboards?\b", ""),
        (r"\bLight\s*Speed\s*II\b", ""),
        (r"\bLightSpeed\s*II\b", ""),
        (r"\bLightspeed\s*II\b", ""),
        (r"\bLight\s*Speed\b", ""),
        (r"\bLightSpeed\b", ""),
        (r"\bLightspeed\b", ""),
        (r"\bBlack\s*Sheep\b", ""),
        (r"\bBlacksheep\b", ""),
        (r"\bStringered\s*Epoxy\b", ""),
        (r"\bWhite\s*Ice\b", ""),
        (r"\bPinline\b", ""),
        (r"\bNew\s*Look\b", ""),
        (r"\bOG\s*Art\b", ""),
        (r"\bNo\s*Tint\b", ""),
        (r"\bWith\s*Tint\b", ""),
        (r"\bWith\s+[^)]*Spray\b", ""),
        (r"\bWith\s*Spray\b", ""),
        (r"\bSpray\b", ""),
        (r"\bEPS\b", ""),
        (r"\bPU\b", ""),
        (r"\bEpoxy\b", ""),
    ]

    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value, flags=re.I)

    value = value.replace("’", "'")
    value = value.replace("Formula-1", "Formula 1")
    value = value.replace("El Patroń", "El Patron")
    value = value.replace("[", "").replace("]", "")
    value = value.replace("(", "").replace(")", "")
    value = value.replace("Sub Driver", "Sub-Driver")
    value = value.replace("Puddle Jummper", "Puddle Jumper")

    value = re.sub(r"[-_/]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = value.title()

    title_replacements = {
        "Rnf": "RNF",
        "Hp": "HP",
        "Xl": "XL",
        "Mr": "MR",
        "Ka": "KA",
        "F1": "F1",
        "V3": "V3",
        "Rv": "RV",
    }

    for old, new in title_replacements.items():
        value = re.sub(rf"\b{old}\b", new, value)

    value = value.replace("3 0", "3.0")
    value = value.replace("2 0", "2.0")
    value = value.replace("RNF '96", "RNF 96")
    value = value.replace("RNF 96Er", "RNF 96er")

    aliases = {
        "Formula 1 Round Pin": "Formula 1 Round",
        "Formula 1 Round Pin Surfboard": "Formula 1 Round",
        "Formula 1 X Yago Dora": "Formula 1 Round",
        "F1 Round": "Formula 1 Round",
        "Mini Driver": "Mini Driver (Re Issue)",
        "Original Puddle Jumper 25": "Original Puddle Jumper '25",
        "Original Puddle Jumper": "Original Puddle Jumper '25",
        "RNF Twinzer 96er": "RNF Twinzer+ '96er",
        "RNF Twinzer 96Er": "RNF Twinzer+ '96er",
        "Ripper Squash": "The Ripper Squash",
        "The Ripper": "The Ripper Squash",
    }

    value = aliases.get(value, value)

    return clean(value)


def get_product_image(product, variant=None):
    if variant:
        featured = variant.get("featured_image") or {}
        if featured.get("src"):
            return featured.get("src")

    images = product.get("images") or []
    if images and images[0].get("src"):
        return images[0].get("src")

    image = product.get("image") or {}
    return image.get("src")


def get_option_map(product, variant):
    option_map = {}

    for option in product.get("options") or []:
        position = option.get("position")
        name = clean(option.get("name")).lower()
        if position and name:
            option_map[name] = variant.get(f"option{position}")

    return option_map


def extract_dimension_text(product, variant):
    option_map = get_option_map(product, variant)

    for key in ["size", "dimensions", "dimension"]:
        value = option_map.get(key)
        if value and "'" in value and "L" in value.upper():
            return clean(value)

    for index in range(1, 4):
        value = variant.get(f"option{index}")
        if value and "'" in value and "L" in value.upper():
            return clean(value)

    title = clean(variant.get("title"))
    if "'" in title and "L" in title.upper():
        return title

    return None


def parse_dimension(value):
    if not value:
        return None

    text = clean(value)
    text = text.replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("×", "x")
    text = re.sub(r"\s*/\s*(FCS\s*II|FCS|Futures?)\b.*$", "", text, flags=re.I)
    text = re.sub(r"^(FCS\s*II|FCS|Futures?)\s*/\s*", "", text, flags=re.I)
    text = text.replace("=", " x ")
    text = re.sub(r"\s+x\s+", " x ", text, flags=re.I)
    text = re.sub(r"(\d+'\s*\d+)", lambda m: m.group(1).replace(" ", ""), text)
    text = re.sub(r"(\d+'\d+)\"", r"\1", text)
    text = re.sub(r"(\d+)'\s+(\d+)", r"\1'\2", text)
    text = re.sub(r"\s+", " ", text).strip()

    volume_match = re.search(r"(\d+(?:\.\d+)?)\s*L\b", text, flags=re.I)
    if not volume_match:
        return None

    volume_litres = float(volume_match.group(1))
    before_volume = text[:volume_match.start()].strip()
    before_volume = re.sub(r"\s+x\s*$", "", before_volume, flags=re.I)

    length_match = re.search(r"(\d+'\d+)", before_volume)
    if not length_match:
        return None

    length = length_match.group(1)
    remaining = before_volume[length_match.end():].strip()
    remaining = remaining.replace('"', "")
    remaining = re.sub(r"\s+x\s+", " ", remaining, flags=re.I)
    remaining = re.sub(r"\s+", " ", remaining).strip()

    tokens = remaining.split(" ")
    dims = []
    index = 0

    while index < len(tokens):
        token = tokens[index]

        if re.fullmatch(r"\d+", token):
            if index + 1 < len(tokens) and re.fullmatch(r"\d+/\d+", tokens[index + 1]):
                dims.append(f"{token} {tokens[index + 1]}")
                index += 2
                continue

            dims.append(token)
            index += 1
            continue

        if re.fullmatch(r"\d+\.\d+", token):
            dims.append(token)
            index += 1
            continue

        if re.fullmatch(r"\d+/\d+", token):
            if dims:
                dims[-1] = f"{dims[-1]} {token}"
            index += 1
            continue

        index += 1

    if len(dims) < 2:
        return None

    width = clean(dims[0])
    thickness = clean(dims[1])

    return {
        "length": length,
        "width": width,
        "thickness": thickness,
        "volume_litres": volume_litres,
    }


def build_catalogue():
    print("")
    print("=" * 80)
    print("Fetching Lost AU shop all catalogue")
    print(SHOP_ALL_URL)
    print("=" * 80)

    data = fetch_json(SHOP_ALL_URL)
    products = data.get("products", [])

    rows = []
    failures = []
    variant_summary = []

    print(f"Products found: {len(products)}")

    for product in products:
        if not is_surfboard_product(product):
            continue

        product_title = clean(product.get("title"))
        model = normalise_model_name(product_title)
        construction = infer_construction(product)
        product_url = f"{SITE_BASE_URL}/products/{product.get('handle')}"
        description = strip_html(product.get("body_html"))

        for variant in product.get("variants") or []:
            dimension_text = extract_dimension_text(product, variant)
            parsed = parse_dimension(dimension_text)

            if not parsed:
                failures.append({
                    "product": product_title,
                    "variant": clean(variant.get("title")),
                    "reason": "no dimensions found",
                })
                continue

            variant_summary.append({
                "brand": BRAND_NAME,
                "model_name": model,
                "construction": construction,
                "length_feet_inches": parsed["length"],
                "width": parsed["width"],
                "thickness": parsed["thickness"],
                "volume_litres": parsed["volume_litres"],
                "product_title": product_title,
                "product_url": product_url,
                "variant_title": clean(variant.get("title")),
                "variant_id": variant.get("id"),
                "sku": variant.get("sku"),
                "available": bool(variant.get("available")),
                "price": variant.get("price"),
            })

            rows.append({
                "brand": BRAND_NAME,
                "model_name": model,
                "model_family": model,
                "board_category": "Surfboard",
                "description": description,
                "length_feet_inches": parsed["length"],
                "width": parsed["width"],
                "thickness": parsed["thickness"],
                "volume_litres": parsed["volume_litres"],
                "construction": construction,
                "fin_setup": None,
                "tail_shape": None,
                "official_product_url": product_url,
                "official_image_url": get_product_image(product, variant),
                "source": SOURCE_NAME,
                "is_active": True,
            })

    deduped_by_key = {}

    for row in rows:
        key = (
            row["model_name"].lower(),
            row["construction"].lower(),
            row["length_feet_inches"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
        )

        existing = deduped_by_key.get(key)

        if existing is None:
            deduped_by_key[key] = row
            continue

        existing_url = existing.get("official_product_url", "").lower()
        current_url = row.get("official_product_url", "").lower()

        if "spray" in existing_url and "spray" not in current_url:
            deduped_by_key[key] = row

    deduped = sorted(
        deduped_by_key.values(),
        key=lambda row: (
            row["model_name"].lower(),
            row["construction"].lower(),
            row["length_feet_inches"],
        ),
    )

    RAW_PRODUCTS_FILE.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    VARIANT_SUMMARY_FILE.write_text(json.dumps(variant_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    CATALOGUE_FILE.write_text(json.dumps(deduped, indent=2, ensure_ascii=False), encoding="utf-8")

    models = sorted(set(row["model_name"] for row in deduped))
    constructions = sorted(set(row["construction"] for row in deduped))
    official_domains = sorted(set(row["official_product_url"].split("/products/")[0] for row in deduped))

    REPORT_FILE.write_text(
        json.dumps(
            {
                "brand": BRAND_NAME,
                "region": REGION_CODE,
                "source": SOURCE_NAME,
                "source_url": SHOP_ALL_URL,
                "products_found": len(products),
                "catalogue_rows": len(deduped),
                "variant_rows": len(variant_summary),
                "models": len(models),
                "model_names": models,
                "constructions": constructions,
                "official_domains": official_domains,
                "failures": failures,
                "catalogue_output_file": str(CATALOGUE_FILE),
                "variant_summary_file": str(VARIANT_SUMMARY_FILE),
                "raw_products_file": str(RAW_PRODUCTS_FILE),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("=" * 80)
    print("LOST AU MASTER CATALOGUE COMPLETE")
    print("=" * 80)
    print("Products:", len(products))
    print("Models:", len(models))
    print("Catalogue rows:", len(deduped))
    print("Variant rows:", len(variant_summary))
    print("Constructions:", constructions)
    print("Official domains:", official_domains)
    print("Failures:", len(failures))
    print("Output:", CATALOGUE_FILE)
    print("Variant summary:", VARIANT_SUMMARY_FILE)
    print("Report:", REPORT_FILE)


if __name__ == "__main__":
    build_catalogue()
