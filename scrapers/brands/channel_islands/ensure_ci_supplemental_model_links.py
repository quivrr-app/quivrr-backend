import json
from pathlib import Path

LINKS_PATH = Path("scrapers/brands/channel_islands/output/ci_canonical_model_links.json")

SUPPLEMENTAL_MODELS = [
    {
        "slug": "better-everyday",
        "model_name": "Better Everyday",
        "product_url": "https://cisurfboards.com/products/better-everyday",
        "region": "global",
        "source": "supplemental-global",
    },
    {
        "slug": "happy-everyday",
        "model_name": "Happy Everyday",
        "product_url": "https://cisurfboards.com/products/happy-everyday",
        "region": "global",
        "source": "supplemental-global",
    },
    {
        "slug": "g-skate",
        "model_name": "G Skate",
        "product_url": "https://cisurfboards.com/products/g-skate",
        "region": "global",
        "source": "supplemental-global",
    },
    {
        "slug": "twin-pin",
        "model_name": "Twin Pin",
        "product_url": "https://cisurfboards.com/products/twin-pin",
        "region": "global",
        "source": "supplemental-global",
    },
]

def main():
    rows = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
    existing = {row.get("slug") for row in rows}

    added = 0

    for row in SUPPLEMENTAL_MODELS:
        if row["slug"] not in existing:
            rows.append(row)
            existing.add(row["slug"])
            added += 1

    rows.sort(key=lambda item: item.get("model_name", "").lower())
    LINKS_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"CI supplemental model links checked. Added: {added}")

if __name__ == "__main__":
    main()
