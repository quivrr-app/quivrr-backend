import json
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.common.board_parser import parse_board


INPUT_FILE = Path("scrapers/products/output/likely_surfboards.json")
OUTPUT_FILE = Path("scrapers/products/output/normalised_surfboards.json")


DIMENSION_PATTERN = re.compile(
    r"(?P<length>\d{1,2}['’]\d{0,2})"
    r'(?:["”]?)\s*(?:x\s*)?'
    r"(?P<width>\d{1,2}(?:\.\d+)?(?:\s+\d{1,2}\/\d{1,2})?)"
    r'(?:["”]?)\s*(?:x\s*)?'
    r"(?P<thickness>\d(?:\.\d+)?(?:\s+\d{1,2}\/\d{1,2})?)"
    r'(?:["”]?)'
)

LITRE_PATTERN = re.compile(
    r"\b(\d{2,3}(?:\.\d+)?)\s?(?:l|lt|ltr|litre|litres)\b",
    re.IGNORECASE,
)


def clean_text(value):
    return (value or "").strip()


def first_non_empty(*values):
    for value in values:
        if value is not None and str(value).strip() != "":
            return value

    return None


def clean_dimension_value(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = (
        value.replace("’", "'")
        .replace("‘", "'")
        .replace("″", '"')
        .replace("“", '"')
        .replace("”", '"')
        .replace("′", "'")
    )

    if re.fullmatch(r"\d{1,2}'", value):
        value = f"{value}0"

    value = value.replace('"', "").strip()
    value = re.sub(r"\s+", " ", value)

    return value if value else None


def looks_like_html(value):
    if value is None:
        return False

    text = str(value).lower()

    return "<" in text or ">" in text or "class=" in text or "</" in text


def looks_like_sku(value):
    if value is None:
        return False

    text = str(value).strip()

    return bool(re.fullmatch(r"[0-9]{8,}", text))


def is_valid_length(value):
    value = clean_dimension_value(value)

    if not value:
        return False

    match = re.fullmatch(r"(?:[4-9]|1[0-2])'[0-9]{1,2}", value)

    if not match:
        return False

    try:
        inches = int(value.split("'")[1])
    except Exception:
        return False

    return 0 <= inches <= 12


def is_valid_width(value):
    value = clean_dimension_value(value)

    if not value:
        return False

    if looks_like_html(value) or looks_like_sku(value):
        return False

    if len(value) > 20:
        return False

    if "stock" in value.lower():
        return False

    if re.fullmatch(r"\d{1,2}(?:\.\d+)?(?:\s\d\/\d)?", value):
        try:
            whole = float(value.split()[0])
        except Exception:
            return False

        return 10 <= whole <= 30

    return False


def is_valid_thickness(value):
    value = clean_dimension_value(value)

    if not value:
        return False

    if looks_like_html(value) or looks_like_sku(value):
        return False

    if len(value) > 20:
        return False

    if "stock" in value.lower():
        return False

    if re.fullmatch(r"\d(?:\.\d+)?(?:\s\d{1,2}\/\d{1,2})?", value):
        try:
            whole = float(value.split()[0])
        except Exception:
            return False

        return 1 <= whole <= 5

    return False


def safe_length(*values):
    for value in values:
        cleaned = clean_dimension_value(value)

        if is_valid_length(cleaned):
            return cleaned

    return None


def safe_width(*values):
    for value in values:
        cleaned = clean_dimension_value(value)

        if is_valid_width(cleaned):
            return cleaned

    return None


def safe_thickness(*values):
    for value in values:
        cleaned = clean_dimension_value(value)

        if is_valid_thickness(cleaned):
            return cleaned

    return None


def extract_dimensions(text):
    if not text:
        return None

    match = DIMENSION_PATTERN.search(text)

    if not match:
        return None

    return {
        "length": clean_dimension_value(match.group("length")),
        "width": clean_dimension_value(match.group("width")),
        "thickness": clean_dimension_value(match.group("thickness")),
    }


def extract_volume(text):
    if not text:
        return None

    match = LITRE_PATTERN.search(text)

    if not match:
        return None

    try:
        return float(match.group(1))
    except Exception:
        return None


def create_model_key(vendor, title, parsed_brand=None):
    base = f"{vendor} {title}".lower()

    remove_terms = [
        "surfboard",
        "surf board",
        "futures",
        "fcs ii",
        "fcs2",
        "fcs",
        "hex core",
        "clear",
        "hyfi 3.0",
        "hyfi 2.0",
        "hyfi",
        "eps",
        "pu",
        "carbon",
        "softboard",
        "soft top",
        "easy rider",
    ]

    if parsed_brand:
        remove_terms.append(parsed_brand.lower())

    for term in remove_terms:
        term_pattern = re.compile(
            rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])",
            re.IGNORECASE,
        )
        base = term_pattern.sub(" ", base)

    base = re.sub(r"\d{1,2}['’]\d{1,2}", "", base)
    base = re.sub(r"\d{2}(?:\.\d+)?\s?l", "", base, flags=re.IGNORECASE)
    base = re.sub(r"\s+", " ", base)

    return base.strip()


def main():
    products = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    output = []

    for item in products:
        title = clean_text(item.get("title"))
        variant = clean_text(
            first_non_empty(
                item.get("variant_title"),
                item.get("variant"),
            )
        )
        vendor = clean_text(item.get("vendor"))
        description = clean_text(item.get("description"))

        combined = f"{vendor} {title} {variant} {description}".strip()

        parsed = parse_board(combined)

        dimensions = extract_dimensions(combined)
        volume = extract_volume(combined)

        source_length = first_non_empty(item.get("length"))
        source_width = first_non_empty(item.get("width"))
        source_thickness = first_non_empty(item.get("thickness"))
        source_volume = first_non_empty(item.get("volume_litres"), item.get("volume"))

        length = safe_length(
            source_length,
            parsed.get("length"),
            dimensions["length"] if dimensions else None,
        )

        width = safe_width(
            source_width,
            dimensions["width"] if dimensions else None,
        )

        thickness = safe_thickness(
            source_thickness,
            dimensions["thickness"] if dimensions else None,
        )

        volume_litres = first_non_empty(
            source_volume,
            parsed.get("volume_litres"),
            volume,
        )

        normalised = {
            "retailer": item.get("retailer"),
            "website": first_non_empty(
                item.get("website"),
                item.get("retailer_url"),
            ),
            "vendor": vendor,
            "title": title,
            "variant_title": variant,
            "variant": variant,
            "variant_source": item.get("variant_source"),
            "brand": first_non_empty(
                parsed.get("brand"),
                item.get("brand"),
            ),
            "model_key": create_model_key(vendor, title, parsed.get("brand")),
            "length": length,
            "width": width,
            "thickness": thickness,
            "volume_litres": volume_litres,
            "construction": first_non_empty(
                parsed.get("construction"),
                item.get("construction"),
            ),
            "fin_system": first_non_empty(
                parsed.get("fin_system"),
                item.get("fin_system"),
            ),
            "price": item.get("price"),
            "available": item.get("available"),
            "stock_quantity": item.get("stock_quantity"),
            "sku": item.get("sku"),
            "product_url": item.get("product_url"),
            "images": item.get("images", []),
            "surfboard_confidence": item.get("surfboard_confidence"),
            "surfboard_match_reasons": item.get("surfboard_match_reasons"),
            "retailer_domain": item.get("retailer_domain"),
        }

        output.append(normalised)

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Input products: {len(products)}")
    print(f"Normalised products: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
