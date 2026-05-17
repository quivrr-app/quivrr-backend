from pathlib import Path

path = Path("scrapers/brands/pyzel/build_pyzel_master_catalogue.py")

content = r'''
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.brands.common_shopify_catalogue import build_catalogue


OUTPUT_FILE = Path("scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json")


MODEL_PRIORITY = [
    "Pyzalien 2 XL Electralite",
    "Pyzalien 2 Electralite",
    "Phantom XL Electralite",
    "Phantom Electralite",
    "Mini Ghost Round",
    "Mini Ghost Squash",
    "Ghost Swallow",
    "Ghost 5 Fin",
    "Ghost Pro",
    "Ghost XL",
    "Ghost",
    "Pyzalien 2 XL",
    "Pyzalien 2",
    "Pyzalien",
    "Phantom Round",
    "Phantom Squash",
    "Phantom XL",
    "Phantom",
    "Astro Glider",
    "Astro Pop XL",
    "Astro Pop",
    "Gremlin XL",
    "Gremlin",
    "Happy Twin",
    "Precious",
    "Tiger Twin",
    "White Tiger",
    "Wildcat",
    "Next Step",
    "Tank",
    "Padillac",
    "Puerto Padi",
    "Mini Padillac",
    "Mid Length Crisis",
    "Crisis Twin",
    "Score Lord",
    "Highline",
    "Radius Prime Round",
    "Radius Prime Squash",
    "Radius",
    "Power Tiger Grom",
    "Power Tiger XL",
    "Power Tiger",
    "Red Tiger XL",
    "Red Tiger",
    "Shadow XL",
    "Shadow",
    "Electralite",
]


def clean_text(value):
    value = str(value or "")
    value = value.replace("GROMlin", "Gromlin")
    value = re.sub(r"\((round|squash|swallow)\)", r" \1 ", value, flags=re.I)
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    value = re.sub(r"\s+", " ", value).strip()
    return value


def title_case_model(model):
    replacements = {
        "XL": "XL",
        "EPS": "EPS",
        "PU": "PU",
    }

    words = model.split()
    output = []

    for word in words:
        upper = word.upper()
        if upper in replacements:
            output.append(replacements[upper])
        else:
            output.append(word.capitalize())

    return " ".join(output)


def canonical_model(raw_model):
    text = clean_text(raw_model)

    for model in MODEL_PRIORITY:
        key = clean_text(model)
        if key in text:
            return model

    text = re.sub(r"\b(electralite|eps|pu)\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return None

    return title_case_model(text)


def normalise_construction(model, source_title):
    text = clean_text(f"{model} {source_title}")

    if "eps" in text or "electralite" in text:
        return "EPS"

    return "PU"


def main():
    build_catalogue(
        brand_name="Pyzel",
        base_url="https://pyzelsurfboards.com",
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

    report_file = OUTPUT_FILE.with_name("pyzel_master_catalogue_clean_report.json")
    report_file.write_text(
        json.dumps(
            {
                "brand": "Pyzel",
                "rows_after_pyzel_cleanup": len(cleaned),
                "models_after_pyzel_cleanup": sorted(set(row["model"] for row in cleaned)),
                "constructions_after_pyzel_cleanup": sorted(set(row["construction"] for row in cleaned)),
                "output_file": str(OUTPUT_FILE),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print("Pyzel brand specific cleanup complete")
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
