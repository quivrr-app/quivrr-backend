import json
import re
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/stockists/output/stockist_candidates.json")
OUTPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities.json")

SURF_TERMS = [
    "surf",
    "surfboards",
    "board",
    "boards",
    "boardstore",
    "boardriders",
    "empire",
    "surfection",
    "aloha",
    "beach beat",
    "trigger",
    "strapper",
    "sanbah",
    "slimes",
    "kirra",
    "wicks"
]

BAD_TERMS = [
    "copyright",
    "javascript",
    "cookie",
    "privacy",
    "instagram",
    "facebook",
    "youtube",
    "wishlist",
    "login",
    "account",
    "search",
    "filter",
    "loading",
    "menu",
    "navigation"
]

def clean(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    return value

def looks_like_store(value):
    lower = value.lower()

    if len(value) < 4 or len(value) > 80:
        return False

    if any(bad in lower for bad in BAD_TERMS):
        return False

    if any(term in lower for term in SURF_TERMS):
        return True

    words = value.split()

    if len(words) >= 2 and all(word[:1].isupper() for word in words[:2]):
        return True

    return False

def main():
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    retailers = {}
    retailer_sources = {}

    for brand_entry in data:
        brand = brand_entry["brand"]

        for candidate in brand_entry["candidates"]:
            candidate = clean(candidate)

            if not looks_like_store(candidate):
                continue

            key = candidate.lower()

            if key not in retailers:
                retailers[key] = candidate
                retailer_sources[key] = []

            retailer_sources[key].append(brand)

    output = []

    for key in sorted(retailers.keys()):
        output.append({
            "retailer_name": retailers[key],
            "source_brands": sorted(list(set(retailer_sources[key]))),
            "brand_count": len(set(retailer_sources[key]))
        })

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Retailers extracted: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
