import json
from pathlib import Path

path = Path("scrapers/brands/lost/output/lost_master_catalogue_clean.json")

data = json.loads(path.read_text(encoding="utf-8"))

print("")
print("=" * 80)
print("LOST QUALITY CHECK")
print("=" * 80)

print("")
print("Rows:", len(data))

models = sorted(set(x["model"] for x in data))
print("Models:", len(models))

print("")
print("Constructions:")
for construction in sorted(set(x["construction"] for x in data)):
    count = len([x for x in data if x["construction"] == construction])
    print(construction, count)

print("")
print("Sample models:")
for model in models[:40]:
    constructions = sorted(set(
        x["construction"]
        for x in data
        if x["model"] == model
    ))

    print(model, "->", constructions)

print("")
print("Sample rows:")
for row in data[:10]:
    print(
        row["model"],
        row["construction"],
        row["length"],
        row["volume_litres"],
    )
