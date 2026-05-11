import json
import re
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_au_review.json")
OUTPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_au_strict.json")

KNOWN_AU_RETAILERS = [
    "natural necessity", "strapper", "surf 3181", "surf culture", "aloha surf manly",
    "beach beat", "big drop surf", "big surf", "boardriders coolangatta",
    "cordingley", "corner surf", "extreme boardriders", "fullcircle surf",
    "hollow surf", "innertube", "kirra surf", "sanbah", "slimes",
    "surfboard empire", "wicks", "surfection", "trigger", "long reef",
    "groove surf", "ocean addicts", "surf fx", "yallingup", "star surf",
    "red herring", "overboard", "akwa surf", "coopers surf"
]

AU_LOCATION_TERMS = [
    "australia", "nsw", "qld", "vic", "wa", "tas", "sa", "act", "nt",
    "sydney", "manly", "brookvale", "collaroy", "narrabeen", "bondi",
    "cronulla", "newcastle", "central coast", "coffs", "byron", "wollongong",
    "gold coast", "burleigh", "coolangatta", "mermaid", "noosa",
    "sunshine coast", "alexandra headland", "caloundra", "coolum",
    "torquay", "melbourne", "frankston", "mornington", "phillip island",
    "margaret river", "yallingup", "perth", "mandurah", "geraldton",
    "adelaide", "glenelg", "burnie", "hobart"
]

NON_AU_LOCATION_TERMS = [
    "o'ahu", "maui", "big island", "hawaii", "honolulu", "california",
    "huntington", "encinitas", "ventura", "hermosa", "jax beach",
    "st. augustine", "new york", "new jersey", "carolina beach",
    "florida", "fort lauderdale", "margate", "ocean city", "usa",
    "united states", "hong kong", "new zealand", "france", "spain",
    "portugal", "uk", "japan", "bali", "indonesia", "mexico"
]

BAD_EXACT = {
    "surfboards", "board bags", "longboards", "shortboards", "boardshorts",
    "longboard", "boards", "surf", "softboards", "all surfboards",
    "shop surfboards", "board store", "new boards", "factory 2nd boards",
    "day boards bags", "boards with spray", "all race boards", "classic longboard",
    "funboard", "bodyboard", "beginner surfboards", "board construction",
    "board mount", "foildrive board", "create your custom board"
}

BAD_CONTAINS = [
    "shipping", "homepage", "review", "waiver", "tshirt", "collection",
    "models", "range", "privacy", "cookie", "wishlist", "account",
    "filter", "facebook", "instagram", "youtube", ".jpg", ".png", ".webp",
    ".com", "@", "find your local", "distribution by", "usa"
]

def clean_name(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    value = value.strip("–-:|")
    return value

def has_any(text, terms):
    lower = f" {text.lower()} "
    return any(term in lower for term in terms)

def keep(item):
    name = clean_name(item.get("retailer_name", ""))
    lower = name.lower()

    if not name or len(name) < 4 or len(name) > 70:
        return False

    if lower in BAD_EXACT:
        return False

    if any(term in lower for term in BAD_CONTAINS):
        return False

    if has_any(name, NON_AU_LOCATION_TERMS):
        return False

    if has_any(name, KNOWN_AU_RETAILERS):
        return True

    if has_any(name, AU_LOCATION_TERMS):
        return True

    return False

def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    output = []
    seen = set()

    for item in data:
        name = clean_name(item.get("retailer_name", ""))

        if not keep(item):
            continue

        key = name.lower()

        if key in seen:
            continue

        seen.add(key)

        output.append({
            "retailer_name": name,
            "source_brands": item.get("source_brands", []),
            "brand_count": item.get("brand_count", 0),
            "review_status": "strict_au_candidate"
        })

    output.sort(key=lambda x: (-x["brand_count"], x["retailer_name"].lower()))

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Input: {len(data)}")
    print(f"Strict AU candidates: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
