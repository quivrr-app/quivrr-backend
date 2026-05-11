import json
import re
from pathlib import Path
from collections import defaultdict

INPUT_FILE = Path("scrapers/products/output/normalised_surfboards.json")
OUTPUT_FILE = Path("scrapers/products/output/grouped_inventory_index.json")

def clean_key(value):
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9\.]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value

def price_float(value):
    try:
        return float(value)
    except:
        return None

def group_key(item):
    parts = [
        clean_key(item.get("vendor")),
        clean_key(item.get("model_key")),
        clean_key(item.get("length")),
        str(item.get("volume_litres") or "")
    ]
    return "|".join(parts)

def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    groups = defaultdict(list)

    for item in data:
        if item.get("available") is not True:
            continue

        key = group_key(item)
        groups[key].append(item)

    output = []

    for key, items in groups.items():
        prices = [price_float(x.get("price")) for x in items]
        prices = [p for p in prices if p is not None]

        retailers = sorted(set(x.get("retailer") for x in items if x.get("retailer")))

        cheapest = None
        priced_items = [x for x in items if price_float(x.get("price")) is not None]

        if priced_items:
            cheapest = min(priced_items, key=lambda x: price_float(x.get("price")))

        sample = items[0]

        output.append({
            "group_key": key,
            "vendor": sample.get("vendor"),
            "title": sample.get("title"),
            "length": sample.get("length"),
            "volume_litres": sample.get("volume_litres"),
            "available_count": len(items),
            "retailer_count": len(retailers),
            "retailers": retailers,
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
            "cheapest_retailer": cheapest.get("retailer") if cheapest else None,
            "cheapest_url": cheapest.get("product_url") if cheapest else None,
            "items": items
        })

    output.sort(key=lambda x: (-x["retailer_count"], x["min_price"] if x["min_price"] is not None else 999999))

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Available records grouped: {sum(len(v) for v in groups.values())}")
    print(f"Inventory groups: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
