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
    except Exception:
        return None


def first_image(item):
    images = item.get("images") or []

    if isinstance(images, list) and images:
        return images[0]

    return None


def board_group_key(item):
    parts = [
        clean_key(item.get("brand") or item.get("vendor")),
        clean_key(item.get("model_key")),
        clean_key(item.get("length")),
        str(item.get("volume_litres") or ""),
    ]

    return "|".join(parts)


def listing_key(item):
    parts = [
        clean_key(item.get("retailer")),
        clean_key(item.get("product_url")),
        clean_key(item.get("sku")),
        clean_key(item.get("variant_title")),
    ]

    return "|".join(parts)


def dedupe_listings(items):
    deduped = {}

    for item in items:
        key = listing_key(item)

        if key not in deduped:
            deduped[key] = item
            continue

        existing_price = price_float(deduped[key].get("price"))
        new_price = price_float(item.get("price"))

        if existing_price is None and new_price is not None:
            deduped[key] = item
        elif existing_price is not None and new_price is not None and new_price < existing_price:
            deduped[key] = item

    return list(deduped.values())


def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    groups = defaultdict(list)

    for item in data:
        if item.get("available") is not True:
            continue

        key = board_group_key(item)
        groups[key].append(item)

    output = []
    total_available = 0
    total_deduped = 0

    for key, raw_items in groups.items():
        total_available += len(raw_items)

        items = dedupe_listings(raw_items)
        total_deduped += len(items)

        prices = [price_float(x.get("price")) for x in items]
        prices = [p for p in prices if p is not None]

        retailers = sorted(
            set(x.get("retailer") for x in items if x.get("retailer"))
        )

        priced_items = [
            x for x in items
            if price_float(x.get("price")) is not None
        ]

        cheapest = None

        if priced_items:
            cheapest = min(priced_items, key=lambda x: price_float(x.get("price")))

        sample = items[0]

        output.append(
            {
                "group_key": key,
                "brand": sample.get("brand") or sample.get("vendor"),
                "vendor": sample.get("vendor"),
                "title": sample.get("title"),
                "model_key": sample.get("model_key"),
                "construction": sample.get("construction"),
                "fin_system": sample.get("fin_system"),
                "length": sample.get("length"),
                "width": sample.get("width"),
                "thickness": sample.get("thickness"),
                "volume_litres": sample.get("volume_litres"),
                "available_count": len(items),
                "raw_available_count": len(raw_items),
                "retailer_count": len(retailers),
                "retailers": retailers,
                "min_price": min(prices) if prices else None,
                "max_price": max(prices) if prices else None,
                "cheapest_retailer": cheapest.get("retailer") if cheapest else None,
                "cheapest_url": cheapest.get("product_url") if cheapest else None,
                "cheapest_price": price_float(cheapest.get("price")) if cheapest else None,
                "image_url": first_image(cheapest or sample),
                "retailer_logo_url": None,
                "items": items,
            }
        )

    output.sort(
        key=lambda x: (
            -x["retailer_count"],
            x["min_price"] if x["min_price"] is not None else 999999,
        )
    )

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Available records before dedupe: {total_available}")
    print(f"Available records after dedupe: {total_deduped}")
    print(f"Inventory groups: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()