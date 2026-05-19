from pathlib import Path

path = Path("scrapers/brands/christenson/build_christenson_master_catalogue.py")

path.write_text(r'''
import json
import re
from pathlib import Path


INPUT_FILE = Path("scrapers/brands/christenson/output/christenson_dimension_probe.json")
OUTPUT_FILE = Path("scrapers/brands/christenson/output/christenson_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/christenson/output/christenson_master_catalogue_clean_report.json")


rows = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

catalogue = []

for row in rows:
    model_name = row.get("name")
    url = row.get("url")
    dimensions = row.get("dimensions") or []

    if not model_name or model_name.lower() in ["team", "fish", "learn more"]:
        continue

    for dimension in dimensions:
        parts = re.split(r"\s+x\s+", dimension, flags=re.IGNORECASE)

        if len(parts) != 3:
            continue

        length = parts[0].strip()
        width = parts[1].strip()
        thickness = parts[2].strip()

        volume = None

        volume_match = re.search(
            r"(\d+(?:\.\d+)?)\s*L",
            dimension,
            flags=re.IGNORECASE,
        )

        if volume_match:
            volume = float(volume_match.group(1))

        thickness = re.sub(
            r"\s*-\s*\d+(?:\.\d+)?\s*L$",
            "",
            thickness,
            flags=re.IGNORECASE,
        ).strip()

        catalogue.append({
            "brand": "Christenson",
            "model_name": model_name,
            "model_family": model_name,
            "board_category": "Surfboard",
            "description": None,
            "official_product_url": url,
            "official_image_url": None,
            "recommended_wave_range": None,
            "recommended_surfer_weight": None,
            "length_feet_inches": length,
            "width": width,
            "thickness": thickness,
            "volume_litres": volume,
            "construction": "PU",
            "fin_setup": None,
            "tail_shape": None,
            "source_product_title": model_name,
            "source_variant_title": dimension,
            "source": url,
        })

seen = set()
deduped = []

for row in catalogue:
    key = (
        row["model_name"],
        row["length_feet_inches"],
        row["width"],
        row["thickness"],
        row["construction"],
    )

    if key in seen:
        continue

    seen.add(key)
    deduped.append(row)

deduped.sort(
    key=lambda row: (
        row["model_name"],
        row["length_feet_inches"],
        row["width"],
        row["thickness"],
    )
)

OUTPUT_FILE.write_text(
    json.dumps(deduped, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

REPORT_FILE.write_text(
    json.dumps({
        "rows": len(deduped),
        "models": len(set(row["model_name"] for row in deduped)),
        "models_list": sorted(set(row["model_name"] for row in deduped)),
    }, indent=2),
    encoding="utf-8",
)

print("")
print("=" * 100)
print("CHRISTENSON COMPLETE")
print("=" * 100)
print("Catalogue rows:", len(deduped))
print("Models:", len(set(row["model_name"] for row in deduped)))
print("Output:", OUTPUT_FILE)
'''.strip() + "\n", encoding="utf-8")

print("Replaced Christenson builder with canonical schema")
