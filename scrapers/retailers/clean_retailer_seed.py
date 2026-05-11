import json
from pathlib import Path

SEED_FILE = Path("scrapers/retailers/retailer_seed.json")
OUTPUT_FILE = Path("scrapers/retailers/retailer_seed_clean.json")

KEEP_DIRECT_SHAPERS = {
    "JS Industries",
}

REMOVE_TYPES = {
    "shaper_direct",
    "brand_direct",
    "stockist_source",
    "marketplace_direct_shaper",
}

def main():
    with SEED_FILE.open("r", encoding="utf-8") as f:
        retailers = json.load(f)

    cleaned = []
    removed = []

    for retailer in retailers:
        name = retailer.get("name", "").strip()
        retailer_type = retailer.get("retailer_type", "").strip()

        if name in KEEP_DIRECT_SHAPERS:
            cleaned.append(retailer)
            continue

        if retailer_type in REMOVE_TYPES:
            removed.append(retailer)
            continue

        cleaned.append(retailer)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print(f"Original count: {len(retailers)}")
    print(f"Cleaned count:  {len(cleaned)}")
    print(f"Removed count:  {len(removed)}")
    print("")
    print("Removed entries:")
    for item in removed:
        print(f"- {item.get('name')} [{item.get('retailer_type')}]")

if __name__ == "__main__":
    main()