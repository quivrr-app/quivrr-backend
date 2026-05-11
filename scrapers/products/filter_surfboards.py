import json
import re
from pathlib import Path

INPUT_DIRS = [
    Path("scrapers/products/output/shopify"),
    Path("scrapers/products/output/woocommerce"),
]

OUTPUT_FILE = Path("scrapers/products/output/likely_surfboards.json")

SURFBOARD_BOARD_TYPES = [
    "surfboard",
    "surf board",
    "shortboard",
    "longboard",
    "mid length",
    "midlength",
    "step up",
    "step-up",
    "softboard",
    "foamie",
    "funboard",
    "malibu",
    "mini mal",
    "gun",
    "fish",
    "twin fin",
    "twinfin",
]

SURFBOARD_BRANDS = [
    "js",
    "js industries",
    "channel islands",
    "ci",
    "lost",
    "mayhem",
    "pyzel",
    "firewire",
    "slater designs",
    "dhd",
    "haydenshapes",
    "sharp eye",
    "sharpeye",
    "chilli",
    "rusty",
    "album",
    "christenson",
    "pukas",
    "torq",
    "softlite",
    "mick fanning",
    "nsp",
    "aloha",
    "misfit",
    "dms",
    "simon anderson",
    "chemistry",
    "mctavish",
    "thunderbolt",
    "takayama",
    "walden",
    "bennetts",
]

BOARD_CONSTRUCTIONS = [
    "hyfi",
    "hyfi 3.0",
    "spinetek",
    "thunderbolt",
    "futureflex",
    "dark arts",
    "carbotune",
    "pu",
    "eps",
    "pe",
]

EXCLUDE_TERMS = [
    "boardshort",
    "board short",
    "wetsuit",
    "spring suit",
    "steamer",
    "rash vest",
    "rashguard",
    "tee",
    "t-shirt",
    "shirt",
    "singlet",
    "hood",
    "hoodie",
    "fleece",
    "jumper",
    "jacket",
    "pants",
    "shorts",
    "dress",
    "bikini",
    "cap",
    "hat",
    "beanie",
    "sunscreen",
    "zinc",
    "wax",
    "comb",
    "legrope",
    "leash",
    "tail pad",
    "traction",
    "deck grip",
    "grip pad",
    "fins",
    "fin set",
    "keel fin",
    "thruster fin",
    "quad fin",
    "single fin",
    "sticker",
    "towel",
    "poncho",
    "sock",
    "board sock",
    "cover",
    "stretch cover",
    "board cover",
    "board bag",
    "day bag",
    "travel bag",
    "coffin",
    "accessory",
    "accessories",
    "strap",
    "tie down",
    "roof rack",
    "rack",
    "wall rack",
    "board sling",
    "skate",
    "skateboard",
    "snowboard",
    "sunglasses",
    "watch",
    "gift card",
    "voucher",
    "repair kit",
    "ding repair",
]

LENGTH_PATTERN = re.compile(
    r"\b(?:[4-9]|1[0-2])\s*['’]\s*\d{0,2}\b|"
    r"\b(?:[4-9]|1[0-2])\s*ft\s*\d{0,2}\b",
    re.IGNORECASE,
)

FULL_DIMENSION_PATTERN = re.compile(
    r"\b(?:[4-9]|1[0-2])\s*['’]\s*\d{0,2}\s*"
    r"(?:\"|in)?\s*[xX\*]\s*"
    r"\d{1,2}(?:\s+\d{1,2}/\d{1,2})?(?:\.\d+)?\s*"
    r"(?:\"|in)?\s*[xX\*]\s*"
    r"\d(?:\s+\d{1,2}/\d{1,2})?(?:\.\d+)?",
    re.IGNORECASE,
)

LITRE_PATTERN = re.compile(
    r"\b(?:1[5-9]|[2-7]\d|8[0-5])(?:\.\d{1,2})?\s*l\b",
    re.IGNORECASE,
)

PRICE_PATTERN = re.compile(r"^\d+(?:\.\d{1,2})?$")


def text_blob(item):
    parts = [
        item.get("title"),
        item.get("variant_title"),
        item.get("vendor"),
        item.get("product_type"),
        item.get("sku"),
    ]

    return " ".join([str(p) for p in parts if p]).lower()


def has_excluded_term(text):
    return any(term in text for term in EXCLUDE_TERMS)


def has_board_type(text):
    return any(term in text for term in SURFBOARD_BOARD_TYPES)


def has_board_brand(text):
    return any(
        re.search(rf"\b{re.escape(brand)}\b", text)
        for brand in SURFBOARD_BRANDS
    )


def has_construction(text):
    return any(
        re.search(rf"\b{re.escape(term)}\b", text)
        for term in BOARD_CONSTRUCTIONS
    )


def has_realistic_price(item):
    raw_price = item.get("price")

    if raw_price is None:
        return True

    price = str(raw_price).strip()

    if not PRICE_PATTERN.match(price):
        return True

    try:
        numeric = float(price)
    except ValueError:
        return True

    return numeric >= 250


def is_likely_surfboard(item):
    text = text_blob(item)

    if not text:
        return False

    if has_excluded_term(text):
        return False

    if not has_realistic_price(item):
        return False

    has_length = bool(LENGTH_PATTERN.search(text))
    has_full_dimensions = bool(FULL_DIMENSION_PATTERN.search(text))
    has_litres = bool(LITRE_PATTERN.search(text))

    board_type = has_board_type(text)
    brand = has_board_brand(text)
    construction = has_construction(text)

    confidence = 0

    if has_length:
        confidence += 2

    if has_full_dimensions:
        confidence += 3

    if has_litres:
        confidence += 2

    if board_type:
        confidence += 2

    if brand:
        confidence += 2

    if construction:
        confidence += 1

    return confidence >= 4


def load_items(file_path):
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            if isinstance(data.get("products"), list):
                return data["products"]

            if isinstance(data.get("items"), list):
                return data["items"]

        return []

    except Exception as exc:
        print(f"{file_path.name}: failed to read JSON: {exc}")
        return []


def main():
    output = []
    total_items = 0

    for input_dir in INPUT_DIRS:
        if not input_dir.exists():
            continue

        for file_path in sorted(input_dir.glob("*.json")):
            items = load_items(file_path)
            total_items += len(items)

            matched = [
                item for item in items
                if is_likely_surfboard(item)
            ]

            output.extend(matched)

            print(
                f"{file_path.name}: "
                f"{len(items)} raw -> "
                f"{len(matched)} likely surfboards"
            )

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("")
    print(f"Raw items: {total_items}")
    print(f"Likely surfboards: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
    