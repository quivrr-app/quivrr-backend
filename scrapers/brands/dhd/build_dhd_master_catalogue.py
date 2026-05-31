import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.brands.common_shopify_catalogue import build_catalogue


OUTPUT_FILE = Path("scrapers/brands/dhd/output/dhd_master_catalogue_clean.json")


MODEL_PRIORITY = [
    "Black Diamond Soft Top",
    "Black Diamond EPS",
    "Black Diamond",
    "Phoenix EPS Swallow Tail",
    "Phoenix Flight EPS",
    "Phoenix Flight",
    "Phoenix",
    "EE Juliette Jnr",
    "EE Juliette",
    "EE Juliette Jnr EPS",
    "EE Juliette Jnr",
    "EE Juliette EPS",
    "EE Juliette",
    "Sweet Spot 4.0",
    "DHD 40th Anniversary",
    "40th Anniversary",
    "SG No.8",
    "SG Number 8",
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


ALIASES = {
    "sg no 8": "SG No.8",
    "sg number 8": "SG No.8",
    "40th anniversary": "DHD 40th Anniversary",
    "dhd 40th anniversary": "DHD 40th Anniversary",
    "ee juliette round tail": "EE Juliette",
    "ee juliette rt": "EE Juliette",
    "ee juliette rt jnr": "EE Juliette Jnr",
    "ee juliette jnr eps": "EE Juliette Jnr EPS",
    "ee juliette junior eps": "EE Juliette Jnr EPS",
    "ee juliette jnr": "EE Juliette Jnr",
    "ee juliette junior": "EE Juliette Jnr",
    "ee juliette eps": "EE Juliette EPS",
    "ee juliette": "EE Juliette",
    "mf lightning": "MF Lightning",
    "mf dna jnr": "MF DNA Jnr",
    "mf dna junior": "MF DNA Jnr",
    "mf dna": "MF DNA",
    "mf bolt": "MF Bolt",
    "mf twin": "MF Twin",
    "the twin": "The Twin",
    "mini twin ii": "Mini Twin II",
    "mini twin 2": "Mini Twin II",
    "mini twin": "Mini Twin",
    "phoenix eps swallow tail": "Phoenix EPS Swallow Tail",
    "phoenix flight eps": "Phoenix Flight EPS",
    "phoenix flight": "Phoenix Flight",
    "phoenix": "Phoenix",
    "nexus eps": "Nexus EPS",
    "nexus": "Nexus",
    "black diamond soft top": "Black Diamond Soft Top",
    "black diamond eps": "Black Diamond EPS",
    "black diamond": "Black Diamond",
    "sweet spot 4 0": "Sweet Spot 4.0",
    "sweet spot": "Sweet Spot 4.0",
    "utopia": "Utopia",
    "interceptor": "Interceptor",
    "sandman": "Sandman",
}


def clean_text(value):
    value = str(value or "")
    value = value.replace("&amp;", "and")
    value = re.sub(r"\((round tail|rt)\)", " rt ", value, flags=re.I)
    value = re.sub(r"\bno\.\s*8\b", "no 8", value, flags=re.I)
    value = re.sub(r"[^a-z0-9.]+", " ", value.lower())
    value = value.replace(".", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def canonical_model(raw_model):
    text = clean_text(raw_model)

    for model in MODEL_PRIORITY:
        key = clean_text(model)
        if key in text:
            canonical = ALIASES.get(key)
            return canonical or model

    for key, model in ALIASES.items():
        if key in text:
            return model

    return None


def normalise_construction(model, source_title, source_product_title, product_url):
    text = clean_text(f"{model} {source_title} {source_product_title} {product_url}")

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
    rejected_models = {}

    for row in data:
        source_title = row.get("model") or ""
        source_product_title = row.get("source_product_title") or ""
        product_url = row.get("official_product_url") or ""
        model_source = " ".join([source_title, source_product_title, product_url])
        model = canonical_model(model_source)

        if not model:
            rejected_models[source_title] = rejected_models.get(source_title, 0) + 1
            continue

        row["model"] = model
        row["model_family"] = model
        row["construction"] = normalise_construction(model, source_title, source_product_title, product_url)

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
                "rejected_source_titles": rejected_models,
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
