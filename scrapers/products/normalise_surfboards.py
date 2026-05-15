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
    r"(?P<length>\d['’]\d{1,2})"
    r'(?:["”]?)\s*'
    r"(?P<width>\d{1,2}(?:\s?\d\/\d)?(?:\.\d+)?)?"
    r'?(?:["”]?)?\s*'
    r"(?P<thickness>\d(?:\s?\d\/\d)?(?:\.\d+)?)?"
)

LITRE_PATTERN = re.compile(
    r"(\d{2}(?:\.\d+)?)\s?l",
    re.IGNORECASE,
)


def clean_text(value):
    return (value or "").strip()


def extract_dimensions(text):
    if not text:
        return None

    match = DIMENSION_PATTERN.search(text)

    if not match:
        return None

    return {
        "length": match.group("length"),
        "width": match.group("width"),
        "thickness": match.group("thickness"),
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
        base = base.replace(term, "")

    base = re.sub(r"\d{1,2}['’]\d{1,2}", "", base)
    base = re.sub(r"\d{2}(?:\.\d+)?\s?l", "", base, flags=re.IGNORECASE)
    base = re.sub(r"\s+", " ", base)

    return base.strip()


def first_non_empty(*values):
    for value in values:
        if value is not None and str(value).strip() != "":
            return value

    return None


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

        combined = f"{vendor} {title} {variant}".strip()

        parsed = parse_board(combined)

        dimensions = extract_dimensions(combined)
        volume = extract_volume(combined)

        source_length = first_non_empty(item.get("length"))
        source_width = first_non_empty(item.get("width"))
        source_thickness = first_non_empty(item.get("thickness"))
        source_volume = first_non_empty(item.get("volume_litres"), item.get("volume"))

        length = first_non_empty(
            source_length,
            parsed.get("length"),
            dimensions["length"] if dimensions else None,
        )

        width = first_non_empty(
            source_width,
            dimensions["width"] if dimensions else None,
        )

        thickness = first_non_empty(
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