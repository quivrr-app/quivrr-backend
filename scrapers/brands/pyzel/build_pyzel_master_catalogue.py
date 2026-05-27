import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.brands.common_shopify_catalogue import build_catalogue


OUTPUT_FILE = Path("scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json")


MODEL_PRIORITY = [
    "Mini Ghost Round",
    "Mini Ghost Squash",
    "Pyzalien 2 XL",
    "Pyzalien 2",
    "Pyzalien",
    "Phantom Round",
    "Phantom Squash",
    "Phantom XL",
    "Phantom",
    "Ghost Swallow",
    "Ghost 5 Fin",
    "Ghost Pro",
    "Ghost XL",
    "Ghost",
    "Astro Glider",
    "Astro Pop XL",
    "Astro Pop",
    "Gremlin XL",
    "Gremlin",
    "Gromlin",
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
]


ALIASES = {
    "mini ghost round": "Mini Ghost Round",
    "mini ghost squash": "Mini Ghost Squash",
    "pyzalien 2 xl": "Pyzalien 2 XL",
    "pyzalien 2": "Pyzalien 2",
    "pyzalien": "Pyzalien",
    "phantom round": "Phantom Round",
    "phantom squash": "Phantom Squash",
    "phantom xl": "Phantom XL",
    "phantom": "Phantom",
    "ghost swallow": "Ghost Swallow",
    "ghost 5 fin": "Ghost 5 Fin",
    "ghost pro": "Ghost Pro",
    "ghost xl": "Ghost XL",
    "ghost": "Ghost",
    "astro glider": "Astro Glider",
    "astro pop xl": "Astro Pop XL",
    "astro pop": "Astro Pop",
    "gremlin xl": "Gremlin XL",
    "gremlin": "Gremlin",
    "gromlin": "Gromlin",
    "grom lin": "Gromlin",
    "happy twin": "Happy Twin",
    "precious": "Precious",
    "tiger twin": "Tiger Twin",
    "white tiger": "White Tiger",
    "wildcat": "Wildcat",
    "next step": "Next Step",
    "tank": "Tank",
    "padillac": "Padillac",
    "puerto padi": "Puerto Padi",
    "mini padillac": "Mini Padillac",
    "mid length crisis": "Mid Length Crisis",
    "crisis twin": "Crisis Twin",
    "score lord": "Score Lord",
    "highline": "Highline",
    "radius prime round": "Radius Prime Round",
    "radius prime squash": "Radius Prime Squash",
    "radius": "Radius",
    "power tiger grom": "Power Tiger Grom",
    "power tiger xl": "Power Tiger XL",
    "power tiger": "Power Tiger",
    "red tiger xl": "Red Tiger XL",
    "red tiger": "Red Tiger",
    "shadow xl": "Shadow XL",
    "shadow": "Shadow",
}


def clean_text(value):
    value = str(value or "")
    value = value.replace("&amp;", "and")
    value = re.sub(r"\((round|squash|swallow)\)", r" \1 ", value, flags=re.I)
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    value = re.sub(r"\b(ca|hi|au)\b", " ", value, flags=re.I)
    value = re.sub(r"\b(id|new|used|board|factory|second|2nd)\b", " ", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def canonical_model(source_title, source_product_title, product_url):
    text = clean_text(" ".join([source_title or "", source_product_title or "", product_url or ""]))

    for model in MODEL_PRIORITY:
        key = clean_text(model)
        if key in text:
            return ALIASES.get(key, model)

    return None


def normalise_construction(source_title, source_product_title, product_url):
    text = clean_text(" ".join([source_title or "", source_product_title or "", product_url or ""]))

    if (
        "electralite" in text
        or "electralite plus" in text
        or "eps" in text
        or "epoxy" in text
    ):
        return "EPS"

    return "PU"


def main():
    build_catalogue(
        brand_name="Pyzel",
        base_url="https://pyzelsurf.com.au",
        output_file=str(OUTPUT_FILE),
    )

    data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))

    cleaned = []
    seen = set()
    rejected = {}

    for row in data:
        source_title = row.get("model") or ""
        source_product_title = row.get("source_product_title") or ""
        product_url = row.get("official_product_url") or ""

        model = canonical_model(source_title, source_product_title, product_url)

        if not model:
            rejected[source_title] = rejected.get(source_title, 0) + 1
            continue

        row["model"] = model
        row["model_family"] = model
        row["construction"] = normalise_construction(source_title, source_product_title, product_url)

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
                "rejected_source_titles": rejected,
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
