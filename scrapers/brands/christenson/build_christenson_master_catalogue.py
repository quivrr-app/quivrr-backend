import json
import re
from pathlib import Path


INPUT_FILE = Path("scrapers/brands/christenson/output/christenson_dimension_probe.json")
OUTPUT_FILE = Path("scrapers/brands/christenson/output/christenson_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/christenson/output/christenson_master_catalogue_clean_report.json")

dimension_regex = re.compile(
    r"(?P<length>\d+'\d{1,2})\s*x\s*(?P<width>\d+(?:\s+\d+/\d+|\.\d+)?)\s*x\s*(?P<thickness>\d+(?:\s+\d+/\d+|\.\d+)?)",
    re.IGNORECASE,
)

rows = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

catalogue = []

skip_names = {"team", "fish", "learn more"}

for row in rows:
    model_name = row.get("name")
    url = row.get("url")
    specifications = row.get("specifications") or []

    if not model_name or model_name.lower() in skip_names:
        continue

    for spec in specifications:
        dimension = spec.get("dimension") or ""
        profile = spec.get("profile") or "PU"
        volume = spec.get("volume_litres")

        match = dimension_regex.search(dimension)

        if not match:
            continue

        construction = profile if profile in ["Standard", "Performance"] else "PU"

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
            "length_feet_inches": match.group("length").strip(),
            "width": match.group("width").strip(),
            "thickness": match.group("thickness").strip(),
            "volume_litres": volume,
            "construction": construction,
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
        row["volume_litres"],
        row["construction"],
    )

    if key in seen:
        continue

    seen.add(key)
    deduped.append(row)

deduped.sort(key=lambda row: (row["model_name"], row["construction"], row["length_feet_inches"]))

OUTPUT_FILE.write_text(json.dumps(deduped, indent=2, ensure_ascii=False), encoding="utf-8")

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
