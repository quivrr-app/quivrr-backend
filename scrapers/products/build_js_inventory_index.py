import json
import re
from pathlib import Path
from collections import defaultdict

INPUT_FILE = Path("scrapers/products/output/normalised_surfboards.json")
OUTPUT_FILE = Path("scrapers/products/output/js_inventory_index.json")

JS_MODEL_TERMS = [
    "monsta",
    "xero gravity",
    "xero fusion",
    "xero",
    "black baron",
    "big baron",
    "raging bull",
    "golden child",
    "sub xero",
    "el baron",
    "red baron",
    "flame fish",
    "bullseye",
    "schooner",
    "forget me not",
    "monsta box",
    "black box",
    "psycho nitro",
    "air 17",
    "bull run"
]

BAD_TERMS = [
    "t-shirt", "tee", "shirt", "hat", "cap", "sock", "board sock",
    "cover", "bag", "tail pad", "traction", "fins", "fin set",
    "wax", "legrope", "leash", "sticker", "poster"
]

def clean(value):
    value = (value or "").lower()
    value = value.replace("’", "'")
    value = re.sub(r"[^a-z0-9'\.]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value

def price_float(value):
    try:
        return float(value)
    except:
        return None

def is_js(item):
    vendor = clean(item.get("vendor"))
    title = clean(item.get("title"))
    variant = clean(item.get("variant_title"))
    sku = clean(item.get("sku"))

    text = " ".join([vendor, title, variant, sku])

    if any(bad in text for bad in BAD_TERMS):
        return False

    vendor_or_title_says_js = (
        "js industries" in vendor
        or vendor == "js"
        or title.startswith("js ")
        or " js " in title
        or "js industries" in title
        or "js surfboards" in title
    )

    known_js_model = any(model in text for model in JS_MODEL_TERMS)

    return vendor_or_title_says_js or known_js_model

def model_name(item):
    title = clean(item.get("title"))
    vendor = clean(item.get("vendor"))

    title = title.replace(vendor, "")
    title = title.replace("js industries", "")
    title = title.replace("js surfboards", "")
    title = title.replace("surfboard", "")
    title = title.replace("board", "")
    title = re.sub(r"\s+", " ", title).strip()

    return title.title()

def group_key(item):
    return "|".join([
        "JS Industries",
        clean(model_name(item)),
        clean(item.get("length")),
        str(item.get("volume_litres") or "")
    ])

def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    js_items = [
        item for item in data
        if item.get("available") is True and is_js(item)
    ]

    groups = defaultdict(list)

    for item in js_items:
        groups[group_key(item)].append(item)

    output = []

    for key, items in groups.items():
        prices = [price_float(x.get("price")) for x in items]
        prices = [p for p in prices if p is not None]

        cheapest = None
        priced_items = [x for x in items if price_float(x.get("price")) is not None]

        if priced_items:
            cheapest = min(priced_items, key=lambda x: price_float(x.get("price")))

        retailers = sorted(set(x.get("retailer") for x in items if x.get("retailer")))
        sample = items[0]

        output.append({
            "brand": "JS Industries",
            "model": model_name(sample),
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

    output.sort(key=lambda x: (-x["retailer_count"], x["model"], x["length"] or ""))

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Available JS records: {len(js_items)}")
    print(f"JS inventory groups: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")
    print("")
    print("Top JS matches:")
    for item in output[:30]:
        print(f"- {item['model']} {item['length']} {item['volume_litres']}L | {item['retailer_count']} retailers | ${item['min_price']}")

if __name__ == "__main__":
    main()
