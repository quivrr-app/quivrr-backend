import json
import re
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_au_strict.json")
OUTPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_au_final_candidates.json")

REAL_STORE_TERMS = [
    "surf", "surfboards", "surf shop", "board store", "boardstore",
    "boardriders", "surfection", "sanbah", "slimes", "kirra",
    "strapper", "trigger", "beach beat", "natural necessity",
    "surfboard empire", "aloha surf", "overboard", "red herring",
    "onboard store", "star surf", "extreme boardriders"
]

BAD_EXACT = {
    "new south wales",
    "western australia",
    "south australia",
    "nsw, australia",
    "all traction",
    "all water p2",
    "contact us",
    "contact nsp international",
    "continued on the gold coast!",
    "design development influences",
    "events supplies",
    "find your country’s nsp distributor",
    "front foot",
    "lane splitter swallow",
    "lisa andersen",
    "macao sar",
    "macao sar (mop p)",
    "mounting plates",
    "phoenix eps swallow tail",
    "premium surfboard rentals",
    "premium surfboard rentals - find a firewire fleets location",
    "represented in all the major surf markets around the world",
    "saudi arabia (sar ر.س)",
    "select country",
    "shop traction",
    "simon says",
    "surfer rosa",
    "t&c surf 32 oz pua ting owala"
}

BAD_CONTAINS = [
    "surf coast hwy",
    "junction fair",
    "scarborough wa",
    "bondi nsw",
    "mona vale nsw",
    "australia",
    "surfboard design",
    "surfboards australia",
    "album surf",
    "channel islands",
    "christenson",
    "firewire",
    "sharpeye",
    "softlite",
    "built surfcraft",
    "full price",
    "excludes sale",
    "distribution by",
    "shop 1/",
    "106 ",
    "28/204",
    "6019",
    "3228",
    "2103",
    "2026",
    "2291"
]

def clean_name(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    value = value.strip("–-:|")
    return value

def looks_real(name):
    lower = name.lower().strip()

    if lower in BAD_EXACT:
        return False

    if any(bad in lower for bad in BAD_CONTAINS):
        return False

    if "@" in lower or ".com" in lower:
        return False

    if re.search(r"\b\d{4}\b", name):
        return False

    if len(name) < 4 or len(name) > 55:
        return False

    return any(term in lower for term in REAL_STORE_TERMS)

def normalise_name(name):
    fixes = {
        "Aloha Surf Manly Style": "Aloha Surf Manly",
        "Fullcircle Surf - Phillip Island": "Full Circle Surf",
        "Slimes Board Store Newcastle": "Slimes Newcastle",
        "Slimes Surf": "Slimes Boardstore",
        "Sanbah": "Sanbah Surf Shop"
    }

    return fixes.get(name, name)

def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    output = []
    seen = set()

    for item in data:
        name = clean_name(item.get("retailer_name", ""))
        name = normalise_name(name)

        if not looks_real(name):
            continue

        key = name.lower()

        if key in seen:
            continue

        seen.add(key)

        output.append({
            "retailer_name": name,
            "source_brands": item.get("source_brands", []),
            "brand_count": item.get("brand_count", 0),
            "review_status": "probable_real_au_retailer"
        })

    output.sort(key=lambda x: x["retailer_name"].lower())

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Input: {len(data)}")
    print(f"Final AU candidates: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
