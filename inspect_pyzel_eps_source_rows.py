import json
from pathlib import Path

path = Path("scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json")
data = json.loads(path.read_text(encoding="utf-8"))

keywords = [
    "Mini Ghost",
    "Pyzalien",
    "Phantom",
    "Electralite",
    "EPS",
]

for row in data:
    text = " ".join([
        str(row.get("model") or ""),
        str(row.get("source_product_title") or ""),
        str(row.get("source_variant_title") or ""),
        str(row.get("official_product_url") or ""),
        str(row.get("construction") or ""),
    ])

    if any(k.lower() in text.lower() for k in keywords):
        print("")
        print("model:", row.get("model"))
        print("construction:", row.get("construction"))
        print("source_product_title:", row.get("source_product_title"))
        print("source_variant_title:", row.get("source_variant_title"))
        print("url:", row.get("official_product_url"))
        print("length:", row.get("length"), "volume:", row.get("volume_litres"))
