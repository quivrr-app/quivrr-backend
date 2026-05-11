import json
from pathlib import Path

INPUT_FILE = Path("scrapers/products/output/normalised_surfboards.json")

def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    total = len(data)
    with_length = sum(1 for x in data if x.get("length"))
    with_volume = sum(1 for x in data if x.get("volume_litres"))
    available = sum(1 for x in data if x.get("available") is True)

    retailers = sorted(set(x.get("retailer") for x in data if x.get("retailer")))

    print(f"Total records: {total}")
    print(f"With length: {with_length}")
    print(f"With volume: {with_volume}")
    print(f"Available: {available}")
    print(f"Retailers: {len(retailers)}")
    print("")
    print("Retailers:")
    for r in retailers:
        print(f"- {r}")

if __name__ == "__main__":
    main()
