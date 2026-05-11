import json
from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path("scrapers/brands/output/js_master_catalogue.json")
OUTPUT_FILE = Path("scrapers/brands/output/js_search_index.json")


def size_label(row):
    return (
        f"{row.get('length')} / "
        f"{row.get('width')} / "
        f"{row.get('thickness')} / "
        f"{row.get('volume_litres')}L"
    )


def main():
    rows = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    models = defaultdict(list)

    for row in rows:
        model = row.get("model")
        construction = row.get("construction")

        if not model or not construction:
            continue

        entry = {
            "brand": "JS Industries",
            "model": model,
            "construction": construction,
            "length": row.get("length"),
            "width": row.get("width"),
            "thickness": row.get("thickness"),
            "volume_litres": row.get("volume_litres"),
            "size_label": size_label(row),
            "fin_system": row.get("fin_system"),
            "tail_shape": row.get("tail_shape"),
            "manufacturer_price": row.get("price"),
            "manufacturer_available": row.get("available"),
            "manufacturer_url": row.get("product_url"),
            "image_url": row.get("image_url"),
        }

        models[model].append(entry)

    output = {
        "brand": "JS Industries",
        "models": [],
    }

    for model_name in sorted(models.keys()):
        sizes = sorted(
            models[model_name],
            key=lambda x: (
                x.get("construction") or "",
                x.get("volume_litres") or 0,
                x.get("length") or "",
            ),
        )

        output["models"].append({
            "model": model_name,
            "sizes": sizes,
        })

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Input rows: {len(rows)}")
    print(f"Models: {len(output['models'])}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
    