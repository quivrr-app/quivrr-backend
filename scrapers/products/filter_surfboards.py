import json
import re
from pathlib import Path

INPUT_DIR = Path("scrapers/products/output/shopify")
OUTPUT_FILE = Path("scrapers/products/output/likely_surfboards.json")

SURFBOARD_INCLUDE = [
    "surfboard", "surf board", "shortboard", "longboard", "mid length",
    "midlength", "fish", "twin fin", "twinfin", "step up", "step-up",
    "softboard", "foamie", "gun", "malibu", "mini mal", "funboard",
    "hyfi", "spinetek", "thunderbolt", "futureflex", "dark arts",
    "pu", "eps"
]

SURFBOARD_BRANDS = [
    "js", "js industries", "channel islands", "ci", "lost", "mayhem",
    "pyzel", "firewire", "slater designs", "dhd", "haydenshapes",
    "sharp eye", "sharpeye", "chilli", "rusty", "album", "christenson",
    "pukas", "torq", "softlite", "mick fanning", "nsp", "aloha",
    "misfit", "dms", "simon anderson", "chemistry"
]

EXCLUDE_TERMS = [
    "boardshort", "board short", "wetsuit", "tee", "t-shirt", "shirt",
    "hat", "cap", "beanie", "wax", "legrope", "leash", "tail pad",
    "traction", "deck grip", "fins", "fin set", "sunscreen", "sticker",
    "bag", "cover", "rack", "skate", "skateboard", "snowboard",
    "sunglasses", "watch", "hoodie", "jumper", "pants", "shorts",
    "dress", "bikini", "towel", "poncho",
    "sock",
    "board sock",
    "stretch cover",
    "cover",
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
    "board sling"
]

DIMENSION_PATTERN = re.compile(r"\b[5-9]['’]\s?\d{0,2}\b|\b[5-9]ft\s?\d{0,2}\b", re.IGNORECASE)
LITRE_PATTERN = re.compile(r"\b\d{2}(\.\d)?\s?l\b", re.IGNORECASE)

def text_blob(item):
    parts = [
        item.get("title"),
        item.get("variant_title"),
        item.get("vendor"),
        item.get("product_type"),
        item.get("sku")
    ]
    return " ".join([str(p) for p in parts if p]).lower()

def is_likely_surfboard(item):
    text = text_blob(item)

    if any(term in text for term in EXCLUDE_TERMS):
        return False

    include_score = 0

    if any(term in text for term in SURFBOARD_INCLUDE):
        include_score += 2

    if any(brand in text for brand in SURFBOARD_BRANDS):
        include_score += 2

    if DIMENSION_PATTERN.search(text):
        include_score += 2

    if LITRE_PATTERN.search(text):
        include_score += 2

    return include_score >= 3

def main():
    output = []
    total_items = 0

    for file_path in sorted(INPUT_DIR.glob("*.json")):
        items = json.loads(file_path.read_text(encoding="utf-8"))
        total_items += len(items)

        matched = [item for item in items if is_likely_surfboard(item)]
        output.extend(matched)

        print(f"{file_path.name}: {len(items)} raw -> {len(matched)} likely surfboards")

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