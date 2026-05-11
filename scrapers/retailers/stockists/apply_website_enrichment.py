import json
from pathlib import Path

SEED_FILE = Path("scrapers/retailers/retailer_seed_expanded.json")
ENRICH_FILE = Path("scrapers/retailers/stockists/output/retailer_website_enrichment.json")
OUTPUT_FILE = Path("scrapers/retailers/retailer_seed_expanded_enriched.json")

def key_name(value):
    return value.lower().replace("&", "and").strip()

def main():
    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    enrich = json.loads(ENRICH_FILE.read_text(encoding="utf-8"))

    enrich_map = {
        key_name(item["name"]): item
        for item in enrich
        if item.get("website")
    }

    updated = 0

    for item in seed:
        key = key_name(item.get("name", ""))

        if item.get("website"):
            continue

        if key in enrich_map:
            item["website"] = enrich_map[key]["website"]
            item["verification_status"] = enrich_map[key]["verification_status"]
            updated += 1

    OUTPUT_FILE.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding="utf-8")

    missing = [item["name"] for item in seed if not item.get("website")]

    print(f"Input seed: {len(seed)}")
    print(f"Updated websites: {updated}")
    print(f"Still missing websites: {len(missing)}")
    print("")
    for name in missing:
        print(f"- {name}")
    print("")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
