from pathlib import Path
import json

INPUT_FILE = Path("scrapers/products/output/shopify/js_industries.json")

def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    print(f"Total products: {len(data)}")

    for index, item in enumerate(data[:20], start=1):
        print("\n" + "=" * 80)
        print(f"ITEM {index}")
        print(json.dumps(item, indent=2, ensure_ascii=False)[:4000])

if __name__ == "__main__":
    main()