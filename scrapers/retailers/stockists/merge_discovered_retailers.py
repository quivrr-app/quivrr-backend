import json
from pathlib import Path

SEED_FILE = Path("scrapers/retailers/retailer_seed_clean.json")
DISCOVERY_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_au_final_verified.json")
OUTPUT_FILE = Path("scrapers/retailers/retailer_seed_expanded.json")

def key_name(name):
    return name.lower().replace("&", "and").strip()

def main():
    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    discovered = json.loads(DISCOVERY_FILE.read_text(encoding="utf-8"))

    existing = {key_name(item.get("name", "")) for item in seed}
    expanded = list(seed)
    added = []

    for item in discovered:
        name = item["retailer_name"]

        if key_name(name) in existing:
            continue

        record = {
            "name": name,
            "website": "",
            "country": "Australia",
            "state": "",
            "region_cluster": "",
            "retailer_type": "multi_brand",
            "hardboards": True,
            "priority": 2,
            "verification_status": "stockist_discovered",
            "source_brands": item.get("source_brands", []),
            "brand_count": item.get("brand_count", 0)
        }

        expanded.append(record)
        added.append(name)
        existing.add(key_name(name))

    OUTPUT_FILE.write_text(json.dumps(expanded, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Seed count: {len(seed)}")
    print(f"Discovered count: {len(discovered)}")
    print(f"Added new: {len(added)}")
    print(f"Expanded count: {len(expanded)}")
    print("")
    print("Added:")
    for name in added:
        print(f"- {name}")
    print("")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
