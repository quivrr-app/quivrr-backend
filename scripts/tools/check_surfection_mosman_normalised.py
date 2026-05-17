import json
from pathlib import Path

rows = json.loads(
    Path("scrapers/products/output/normalised_surfboards.json")
    .read_text(encoding="utf-8")
)

matches = [
    row for row in rows
    if str(row.get("retailer", "")).lower() == "surfection mosman"
]

print()
print("Surfection Mosman")
print("normalised rows:", len(matches))

for row in matches[:30]:
    print(
        "-",
        row.get("title") or row.get("raw_title"),
        "|",
        row.get("length"),
        "|",
        row.get("volume_litres")
    )
