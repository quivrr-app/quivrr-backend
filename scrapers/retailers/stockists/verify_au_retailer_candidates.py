import json
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_au_final_candidates.json")
OUTPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_au_final_verified.json")

REMOVE_NAMES = {
    "Nomad Surf Shop - Boynton Beach",
    "Wavelengths Surf Shop - Morro Bay"
}

NORMALISE = {
    "Surf Culture": "Surf Culture Bondi",
    "Strapper Surfboards": "Strapper Surf Torquay",
    "Overboard": "Overboard Surf",
    "Beach Beat": "Beach Beat Surfboards",
    "Surfboard Empire Nobby's": "Surfboard Empire Nobby Beach"
}

def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    output = []
    seen = set()

    for item in data:
        name = item["retailer_name"].strip()

        if name in REMOVE_NAMES:
            continue

        name = NORMALISE.get(name, name)
        key = name.lower()

        if key in seen:
            continue

        seen.add(key)

        output.append({
            **item,
            "retailer_name": name,
            "review_status": "verified_au_candidate"
        })

    output.sort(key=lambda x: x["retailer_name"].lower())

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Input: {len(data)}")
    print(f"Verified AU candidates: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
