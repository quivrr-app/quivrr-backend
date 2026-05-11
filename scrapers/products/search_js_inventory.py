import json
import sys
from pathlib import Path


CATALOGUE_FILE = Path("scrapers/brands/output/js_master_catalogue.json")
INVENTORY_FILE = Path("scrapers/products/output/normalised_surfboards.json")


def clean(value):
    return str(value or "").strip().lower()


def exact_match(value_a, value_b):
    return clean(value_a) == clean(value_b)


def find_manufacturer_results(model, length, construction):
    rows = json.loads(CATALOGUE_FILE.read_text(encoding="utf-8"))

    results = []

    for row in rows:
        if not exact_match(row.get("brand"), "JS Industries"):
            continue

        if not exact_match(row.get("model"), model):
            continue

        if not exact_match(row.get("length"), length):
            continue

        if not exact_match(row.get("construction"), construction):
            continue

        results.append({
            "source_type": "manufacturer",
            "retailer": "JS Industries",
            "brand": row.get("brand"),
            "model": row.get("model"),
            "length": row.get("length"),
            "width": row.get("width"),
            "thickness": row.get("thickness"),
            "volume_litres": row.get("volume_litres"),
            "construction": row.get("construction"),
            "fin_system": row.get("fin_system"),
            "tail_shape": row.get("tail_shape"),
            "price": row.get("price"),
            "available": row.get("available"),
            "product_url": row.get("product_url"),
            "image_url": row.get("image_url"),
            "match_type": "exact",
        })

    return results


def find_retailer_results(model, length, construction):
    rows = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))

    results = []

    model_clean = clean(model)

    for row in rows:
        retailer_name = clean(row.get("retailer"))

        if retailer_name == "js industries":
            continue

        if (
            not exact_match(row.get("brand"), "JS")
            and not exact_match(row.get("brand"), "JS Industries")
        ):
            continue

        title_blob = clean(
            f"{row.get('title')} "
            f"{row.get('variant_title')} "
            f"{row.get('model_key')}"
        )

        if model_clean not in title_blob:
            continue

        if not exact_match(row.get("length"), length):
            continue

        if not exact_match(row.get("construction"), construction):
            continue

        results.append({
            "source_type": "retailer",
            "retailer": row.get("retailer"),
            "website": row.get("website"),
            "brand": row.get("brand"),
            "model": model,
            "title": row.get("title"),
            "variant_title": row.get("variant_title"),
            "length": row.get("length"),
            "width": row.get("width"),
            "thickness": row.get("thickness"),
            "volume_litres": row.get("volume_litres"),
            "construction": row.get("construction"),
            "fin_system": row.get("fin_system"),
            "price": row.get("price"),
            "available": row.get("available"),
            "product_url": row.get("product_url"),
            "images": row.get("images", []),
            "match_type": "exact",
        })

    return results


def search(model, length, construction):
    manufacturer_results = find_manufacturer_results(
        model,
        length,
        construction,
    )

    retailer_results = find_retailer_results(
        model,
        length,
        construction,
    )

    return {
        "query": {
            "brand": "JS Industries",
            "model": model,
            "length": length,
            "construction": construction,
        },
        "total_results": (
            len(manufacturer_results)
            + len(retailer_results)
        ),
        "manufacturer_results": manufacturer_results,
        "retailer_results": retailer_results,
    }


def main():
    if len(sys.argv) < 4:
        print("Usage:")
        print(
            "python scrapers/products/search_js_inventory.py "
            "\"Baron Flyer\" "
            "\"5'11\" "
            "\"PU\""
        )
        sys.exit(1)

    model = sys.argv[1]
    length = sys.argv[2]
    construction = sys.argv[3]

    results = search(
        model,
        length,
        construction,
    )

    print(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
    