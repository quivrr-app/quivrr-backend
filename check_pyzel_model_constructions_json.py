import json
from pathlib import Path

data = json.loads(Path("scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json").read_text(encoding="utf-8"))

for model in ["Mini Ghost Round", "Mini Ghost Squash", "Pyzalien 2", "Pyzalien 2 XL", "Phantom", "Phantom XL"]:
    rows = [r for r in data if r.get("model") == model]
    print("")
    print(model)
    print("rows:", len(rows))
    print("constructions:", sorted(set(r.get("construction") for r in rows)))
    for r in rows[:10]:
        print(r.get("construction"), r.get("length"), r.get("volume_litres"), r.get("source_product_title"))
