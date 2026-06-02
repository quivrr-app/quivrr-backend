import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

OUTPUT_PATH = Path("scrapers/manufacturers/availability/output/lost/lost_au_manufacturer_inventory.json")

BRAND_NAME = "Lost"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"
LOST_AU_BASE_URL = "https://lostsurfboards.com.au"
LOST_AU_PRODUCTS_URL = "https://lostsurfboards.com.au/collections/shop-all/products.json?limit=250"

SURFBOARD_KEYWORDS = [
    "surfboard",
    "driver",
    "sub driver",
    "rocket",
    "puddle",
    "party platter",
    "sabotaj",
    "uber",
    "quiver killer",
    "step driver",
    "speed demon",
    "rnf",
    "rad ripper",
    "crowd killer",
    "evil twin",
    "ka swordfish",
    "california twin",
    "3.0",
]

REJECT_KEYWORDS = [
    "fin",
    "fins",
    "traction",
    "deck grip",
    "tail pad",
    "pad",
    "leash",
    "cover",
    "bag",
    "wax",
    "tee",
    "shirt",
    "hat",
    "cap",
    "beanie",
    "towel",
    "sticker",
    "gift card",
    "plug",
]


def normalise_text(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = value.replace("×", "x")
    value = re.sub(r"\s+", " ", value)

    return value



FRACTION_MAP = {
    "1/16": 0.0625,
    "1/8": 0.125,
    "3/16": 0.1875,
    "1/4": 0.25,
    "5/16": 0.3125,
    "3/8": 0.375,
    "7/16": 0.4375,
    "1/2": 0.5,
    "9/16": 0.5625,
    "5/8": 0.625,
    "11/16": 0.6875,
    "3/4": 0.75,
    "13/16": 0.8125,
    "7/8": 0.875,
    "15/16": 0.9375,
}


def dimension_to_decimal(value):
    value = normalise_text(value)

    if not value:
        return None

    try:
        return f"{float(value):.2f}"
    except Exception:
        pass

    total = 0.0

    for part in value.split():
        if part in FRACTION_MAP:
            total += FRACTION_MAP[part]
            continue

        try:
            total += float(part)
        except Exception:
            return value

    return f"{total:.2f}"


def money_from_cents(value):
    if value is None:
        return None

    try:
        value = float(value)
    except Exception:
        return None

    if value > 10000:
        return round(value / 100.0, 2)

    return round(value, 2)


def is_available(variant):
    if variant.get("available") is True:
        return True

    if variant.get("inventory_quantity") is not None:
        try:
            return int(variant.get("inventory_quantity")) > 0
        except Exception:
            pass

    return False


def looks_like_surfboard(product):
    title = (normalise_text(product.get("title")) or "").lower()
    handle = (normalise_text(product.get("handle")) or "").lower()

    combined = f"{title} {handle}"

    if any(word in combined for word in REJECT_KEYWORDS):
        return False

    if any(word in combined for word in SURFBOARD_KEYWORDS):
        return True

    variants = product.get("variants") or []

    for variant in variants:
        variant_title = (
            normalise_text(variant.get("title")) or ""
        ).lower()

        if re.search(r"\b\d+'\d+", variant_title):
            return True

        if re.search(r"\b\d{1,2}\.\d+\s*l\b", variant_title):
            return True

    return False


def normalise_model_name(product_title):
    title = normalise_text(product_title) or ""

    original_title = title

    construction_suffixes = [
        "Black Sheep",
        "Light Speed II",
        "LightSpeed II",
        "Light Speed",
        "LightSpeed",
    ]

    for suffix in construction_suffixes:
        title = re.sub(
            rf"\b{re.escape(suffix)}\b",
            "",
            title,
            flags=re.IGNORECASE,
        )

    title = re.sub(r"\([^)]*\)", "", title)
    title = re.sub(r"\bwith spray\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\bsurfboard\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" -|")

    aliases = {
        "The Original Puddle Jumper": "Original Puddle Jumper '25",
        "Mini Driver": "Mini Driver (Re Issue)",
        "Formula 1 Round Pin": "Formula 1 Round",
        "Formula 1 x Yago Dora": "Formula 1 Round",
        "RNF Twinzer '96er": "RNF Twinzer+ '96er",
        "RNF '96": "RNF 96",
        "The Ripper": "The Ripper Squash",
        "RNF '96": "RNF 96",
        "The Ripper": "The Ripper Squash",
        "RNF 96er": "RNF 96",
        "RNF 96": "RNF 96",
        "Driver 3.0 Grom": "Driver 3.0 Squash",
    }

    if title in aliases:
        return aliases[title]

    return title or original_title or None


def normalise_construction(value, title=None):
    combined = " ".join([
        str(value or ""),
        str(title or ""),
    ]).lower()

    if "light speed ii" in combined or "lightspeed ii" in combined:
        return "LightSpeed"

    if "light speed" in combined or "lightspeed" in combined:
        return "LightSpeed"

    if "black sheep" in combined:
        return "Black Sheep"

    if "lib tech" in combined or "libtech" in combined:
        return "Lib Tech"

    if "carbon wrap" in combined:
        return "Carbon Wrap"

    if "c4" in combined:
        return "C4"

    if "pu" in combined or "poly" in combined:
        return "PU"

    return "PU"


def normalise_fin_system(value, title=None):
    combined = " ".join([
        str(value or ""),
        str(title or ""),
    ]).lower()

    if "fcs ii" in combined or "fcs2" in combined or "fcsii" in combined:
        return "FCS II"

    if "future" in combined:
        return "Futures"

    if "thruster" in combined:
        return "Thruster"

    if "twin" in combined:
        return "Twin"

    if "quad" in combined:
        return "Quad"

    value = normalise_text(value)

    return value


def parse_dimensions(text):
    text = normalise_text(text) or ""
    text = text.replace('"', "")
    text = text.replace("?", "")
    text = text.replace("?", "")

    length = None
    width = None
    thickness = None
    volume = None

    volume_match = re.search(r"(\d{1,2}(?:\.\d+)?)\s*l\b", text, re.IGNORECASE)

    if volume_match:
        try:
            volume = float(volume_match.group(1))
        except Exception:
            volume = None

    pattern = re.compile(
        r"(?P<length>\d+'\d+)\s+"
        r"(?P<width>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)\s+"
        r"(?P<thickness>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)\s+"
        r"(?P<volume>\d{1,2}(?:\.\d+)?)\s*l\b",
        re.IGNORECASE,
    )

    match = pattern.search(text)

    if match:
        length = normalise_text(match.group("length"))
        width = dimension_to_decimal(match.group("width"))
        thickness = dimension_to_decimal(match.group("thickness"))

        try:
            volume = float(match.group("volume"))
        except Exception:
            pass

        return length, width, thickness, volume

    pattern_with_separators = re.compile(
        r"(?P<length>\d+'\d+)\s*(?:x|X|/|\|)\s*"
        r"(?P<width>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)\s*(?:x|X|/|\|)\s*"
        r"(?P<thickness>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)",
        re.IGNORECASE,
    )

    match = pattern_with_separators.search(text)

    if match:
        length = normalise_text(match.group("length"))
        width = dimension_to_decimal(match.group("width"))
        thickness = dimension_to_decimal(match.group("thickness"))
        return length, width, thickness, volume

    length_match = re.search(r"\b(\d+'\d+)\b", text)

    if length_match:
        length = normalise_text(length_match.group(1))

    return length, width, thickness, volume


def product_url(product, variant):
    handle = product.get("handle")

    if not handle:
        return None

    url = f"{LOST_AU_BASE_URL}/products/{handle}"

    variant_id = variant.get("id")

    if variant_id:
        url = f"{url}?variant={variant_id}"

    return url


def product_image(product):
    image = product.get("image") or {}

    if isinstance(image, dict) and image.get("src"):
        return image.get("src")

    images = product.get("images") or []

    if images and isinstance(images[0], dict):
        return images[0].get("src")

    return None


def fetch_products():
    response = requests.get(
        LOST_AU_PRODUCTS_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
        timeout=45,
    )

    response.raise_for_status()

    payload = response.json()

    return payload.get("products", [])


def main():
    products = fetch_products()

    now = datetime.now(timezone.utc).isoformat()

    output_rows = []
    skipped_non_board = 0
    skipped_unavailable = 0
    skipped_missing_dimensions = 0
    seen = set()

    for product in products:
        if not looks_like_surfboard(product):
            skipped_non_board += 1
            continue

        model = normalise_model_name(product.get("title"))
        image_url = product_image(product)

        for variant in product.get("variants") or []:
            if not is_available(variant):
                skipped_unavailable += 1
                continue

            variant_title = normalise_text(variant.get("title"))
            combined_title = " | ".join(
                value for value in [
                    normalise_text(product.get("title")),
                    variant_title,
                ]
                if value
            )

            length, width, thickness, volume_litres = parse_dimensions(combined_title)

            if not length or volume_litres is None:
                skipped_missing_dimensions += 1
                continue

            construction = normalise_construction(variant_title, combined_title)
            fin_system = normalise_fin_system(variant_title, combined_title)
            url = product_url(product, variant)

            dedupe_key = (
                model,
                length,
                width,
                thickness,
                str(volume_litres),
                construction,
                fin_system,
                str(variant.get("id")),
                url,
            )

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)

            output_rows.append({
                "brandName": BRAND_NAME,
                "modelName": model,
                "lengthFeetInches": length,
                "width": width,
                "thickness": thickness,
                "volumeLitres": volume_litres,
                "construction": construction,
                "finSetup": fin_system,
                "tailShape": None,
                "productUrl": url,
                "productImageUrl": image_url,
                "priceAmount": money_from_cents(variant.get("price")),
                "priceCurrency": "AUD",
                "stockStatus": "available",
                "isAvailable": True,
                "availabilitySource": AVAILABILITY_SOURCE,
                "regionCode": REGION_CODE,
                "sourceProductId": product.get("id"),
                "sourceVariantId": variant.get("id"),
                "sourceVariantTitle": variant_title,
                "sourceCataloguePath": LOST_AU_PRODUCTS_URL,
                "sourceStorefront": LOST_AU_BASE_URL,
                "snapshotUtc": now,
            })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output_rows, indent=2), encoding="utf-8")

    print("Lost AU manufacturer availability build complete")
    print(f"Products seen: {len(products)}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Skipped non board products: {skipped_non_board}")
    print(f"Skipped unavailable variants: {skipped_unavailable}")
    print(f"Skipped missing dimensions: {skipped_missing_dimensions}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
