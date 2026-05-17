import json
from pathlib import Path

files = [
    Path("scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json"),
    Path("scrapers/brands/dhd/output/dhd_master_catalogue_clean.json"),
]

for file in files:
    data = json.loads(file.read_text(encoding="utf-8"))

    models = sorted(set(x.get("model") for x in data if x.get("model")))
    missing_length = [x for x in data if not x.get("length")]
    missing_volume = [x for x in data if x.get("volume_litres") is None]
    missing_width = [x for x in data if not x.get("width")]
    missing_thickness = [x for x in data if not x.get("thickness")]

    print("")
    print("=" * 80)
    print(file)
    print("=" * 80)
    print("Rows:", len(data))
    print("Models:", len(models))
    print("Missing length:", len(missing_length))
    print("Missing volume:", len(missing_volume))
    print("Missing width:", len(missing_width))
    print("Missing thickness:", len(missing_thickness))
    print("")
    print("Sample models:")
    for model in models[:25]:
        print(" -", model)
