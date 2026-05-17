import json
from pathlib import Path

files = [
    Path("scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json"),
    Path("scrapers/brands/dhd/output/dhd_master_catalogue_clean.json"),
]

for file in files:
    data = json.loads(file.read_text(encoding="utf-8"))

    missing_product_url = [x for x in data if not x.get("official_product_url")]
    missing_image_url = [x for x in data if not x.get("official_image_url")]
    constructions = sorted(set(x.get("construction") for x in data if x.get("construction")))
    fin_systems = sorted(set(x.get("fin_system") for x in data if x.get("fin_system")))

    print("")
    print("=" * 80)
    print(file)
    print("=" * 80)
    print("Rows:", len(data))
    print("Missing official product URL:", len(missing_product_url))
    print("Missing official image URL:", len(missing_image_url))
    print("Constructions:", constructions[:40])
    print("Fin systems:", fin_systems[:40])
    print("")
    print("Sample rows:")
    for row in data[:5]:
        print(row.get("model"), row.get("length"), row.get("volume_litres"), row.get("official_image_url"))
