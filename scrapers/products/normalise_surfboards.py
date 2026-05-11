import json
import re
from pathlib import Path

INPUT_FILE = Path("scrapers/products/output/likely_surfboards.json")
OUTPUT_FILE = Path("scrapers/products/output/normalised_surfboards.json")

DIMENSION_PATTERN = re.compile(
    r"(?P<length>\d['’]\d{1,2})"
    r'(?:["”]?)\s*'
    r"(?P<width>\d{1,2}(?:\s?\d\/\d)?(?:\.\d+)?)?"
    r'?(?:["”]?)?\s*'
    r"(?P<thickness>\d(?:\s?\d\/\d)?(?:\.\d+)?)?"
)

LITRE_PATTERN = re.compile(r"(\d{2}(?:\.\d)?)\s?l", re.IGNORECASE)

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
        "thickness": match.group("thickness")
    }

def extract_volume(text):
    if not text:
        return None

    match = LITRE_PATTERN.search(text)

    if not match:
        return None

    try:
        return float(match.group(1))
    except:
        return None

def create_model_key(vendor, title):
    base = f"{vendor} {title}".lower()

    remove_terms = [
        "surfboard",
        "surf board",
        "futures",
        "fcs ii",
        "fcs2",
        "hex core",
        "clear"
    ]

    for term in remove_terms:
        base = base.replace(term, "")

    base = re.sub(r"\s+", " ", base)

    return base.strip()

def main():
    products = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    output = []

    for item in products:
        title = clean_text(item.get("title"))
        variant = clean_text(item.get("variant_title"))
        vendor = clean_text(item.get("vendor"))

        combined = f"{title} {variant}"

        dimensions = extract_dimensions(combined)
        volume = extract_volume(combined)

        normalised = {
            "retailer": item.get("retailer"),
            "website": item.get("website"),

            "vendor": vendor,
            "title": title,
            "variant_title": variant,

            "model_key": create_model_key(vendor, title),

            "length": dimensions["length"] if dimensions else None,
            "width": dimensions["width"] if dimensions else None,
            "thickness": dimensions["thickness"] if dimensions else None,

            "volume_litres": volume,

            "price": item.get("price"),
            "available": item.get("available"),

            "sku": item.get("sku"),

            "product_url": item.get("product_url"),

            "images": item.get("images", [])
        }

        output.append(normalised)

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Input products: {len(products)}")
    print(f"Normalised products: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

    