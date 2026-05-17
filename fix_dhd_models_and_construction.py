from pathlib import Path

path = Path("scrapers/brands/dhd/build_dhd_master_catalogue.py")

content = r'''
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.brands.common_shopify_catalogue import build_catalogue


OUTPUT_FILE = Path("scrapers/brands/dhd/output/dhd_master_catalogue_clean.json")


MODEL_MAP = {
    "mf lightning": "MF Lightning",
    "ee juliette": "EE Juliette",
    "mf dna": "MF DNA",
    "sg number 8": "SG Number 8",
    "40th anniversary": "40th Anniversary",
    "nexus": "Nexus",
    "phoenix flight": "Phoenix Flight",
    "utopia": "Utopia",
    "black diamond": "Black Diamond",
    "black diamond soft top": "Black Diamond Soft Top",
    "interceptor": "Interceptor",
    "sandman": "Sandman",
    "ee juliette round tail": "EE Juliette Round Tail",
    "sweet spot 4.0": "Sweet Spot 4.0",
    "sweet spot": "Sweet Spot 4.0",
    "ee juliette eps": "EE Juliette EPS",
    "ee juliette jnr eps": "EE Juliette Jnr EPS",
    "nexus eps": "Nexus EPS",
    "phoenix flight eps": "Phoenix Flight EPS",
    "black diamond eps": "Black Diamond EPS",
    "phoenix eps swallow tail": "Phoenix EPS Swallow Tail",
    "mf twin": "MF Twin",
    "the twin": "The Twin",
    "mini twin ii": "Mini Twin II",
    "mini twin": "Mini Twin",
    "mf bolt": "MF Bolt",
    "mf dna jnr": "MF DNA Jnr",
    "ee juliette jnr": "EE Juliette Jnr",
}


MODEL_PRIORITY = [
    "Black Diamond Soft Top",
    "Black Diamond EPS",
    "Black Diamond",
    "EE Juliette Round Tail",
    "EE Juliette Jnr EPS",
    "EE Juliette Jnr",
    "EE Juliette EPS",
    "EE Juliette",
    "Phoenix EPS Swallow Tail",
    "Phoenix Flight EPS",
    "Phoenix Flight",
    "Sweet Spot 4.0",
    "SG Number 8",
    "40th Anniversary",
    "MF Lightning",
    "MF DNA Jnr",
    "MF DNA",
    "MF Twin",
    "MF Bolt",
    "Mini Twin II",
    "Mini Twin",
    "The Twin",
    "Nexus EPS",
    "Nexus",
    "Utopia",
    "Interceptor",
    "Sandman",
]


def clean_text(value):
    value = str(value or "")
    value = re.sub(r"[^a-z0-9.]+", " ", value.lower())
    value = re.sub(r"\s+", " ", value).strip()
    return value


def canonical_model(raw_model):
    text = clean_text(raw_model)

    for model in MODEL_PRIORITY:
        key = clean_text(model)
        if key in text:
            return model

    for key, model in MODEL_MAP.items():
        if key in text:
            return model

    return None


def normalise_construction(model, source_title):
    text = clean_text(f"{model} {source_title}")

    if "eps" in text:
        return "EPS"

    if "soft top" in text:
        return "Soft Top"

    return "PU"


def main():
    build_catalogue(
        brand_name="DHD",
        base_url="https://dhdsurf.com",
        output_file=str(OUTPUT_FILE),
    )

    data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))

    cleaned = []
    seen = set()

    for row in data:
        source_title = row.get("model") or ""
        model = canonical_model(source_title)

        if not model:
            continue

        row["model"] = model
        row["model_family"] = model
        row["construction"] = normalise_construction(model, source_title)

        key = (
            row.get("model"),
            row.get("length"),
            row.get("width"),
            row.get("thickness"),
            row.get("volume_litres"),
            row.get("construction"),
            row.get("fin_system"),
        )

        if key in seen:
            continue

        seen.add(key)
        cleaned.append(row)

    OUTPUT_FILE.write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report_file = OUTPUT_FILE.with_name("dhd_master_catalogue_clean_report.json")
    report_file.write_text(
        json.dumps(
            {
                "brand": "DHD",
                "rows_after_dhd_cleanup": len(cleaned),
                "models_after_dhd_cleanup": sorted(set(row["model"] for row in cleaned)),
                "constructions_after_dhd_cleanup": sorted(set(row["construction"] for row in cleaned)),
                "output_file": str(OUTPUT_FILE),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print("DHD brand specific cleanup complete")
    print(f"Rows after cleanup: {len(cleaned)}")
    print(f"Models after cleanup: {len(set(row['model'] for row in cleaned))}")
    print(f"Constructions: {sorted(set(row['construction'] for row in cleaned))}")
    print(f"Output: {OUTPUT_FILE}")
    print("")


if __name__ == "__main__":
    main()
'''

path.write_text(content.strip() + "\n", encoding="utf-8")
print(f"Updated {path}")
