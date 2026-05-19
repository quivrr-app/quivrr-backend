from pathlib import Path

path = Path("scrapers/brands/chilli/build_chilli_master_catalogue.py")

path.write_text(r'''
import json
import time
from pathlib import Path

import requests


BRAND = "Chilli"
MODELS_URL = "https://chilli.shaperbuddy.com/api/v1/surfboardmodels"
DETAIL_URL = "https://chilli.shaperbuddy.com/api/v1/surfboardmodels/{id}?lang=en"

OUTPUT_FILE = Path("scrapers/brands/chilli/output/chilli_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/chilli/output/chilli_master_catalogue_clean_report.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


def clean(value):
    return str(value or "").replace("\\/", "/").strip()


def first_image(detail):
    img_dynamic = detail.get("img_dynamic") or {}
    img = detail.get("img") or {}

    return (
        img_dynamic.get("deck")
        or img_dynamic.get("bottom")
        or img.get("deck")
        or img.get("bottom")
        or detail.get("img_logo")
    )


def normalise_fin_setup(value):
    value = clean(value)

    if not value:
        return None

    value = value.replace("FUTURE", "Futures")
    value = value.replace("FUTURES", "Futures")
    value = value.replace("FCSII", "FCS II")
    value = value.replace("FCS 2", "FCS II")

    return value


def extract_dimension_value(dimension, keys):
    for key in keys:
        value = dimension.get(key)

        if value not in [None, ""]:
            return clean(value)

    return None


def build_catalogue():
    model_response = requests.get(
        MODELS_URL,
        headers=HEADERS,
        timeout=(10, 60),
    )
    model_response.raise_for_status()

    models = model_response.json()

    rows = []
    failures = []

    for model in models:
        model_id = model.get("id_surfboardmodel")
        model_name = clean(model.get("surfboardmodel"))

        detail_response = requests.get(
            DETAIL_URL.format(id=model_id),
            headers=HEADERS,
            timeout=(10, 60),
        )
        detail_response.raise_for_status()

        detail_data = detail_response.json()
        detail = detail_data[0] if isinstance(detail_data, list) and detail_data else {}

        dimensions = detail.get("standard_dimensions") or []

        if not dimensions:
            failures.append({
                "id_surfboardmodel": model_id,
                "model_name": model_name,
                "reason": "no standard dimensions",
            })
            continue

        category = (
            clean(detail.get("surfboardmodeltypename"))
            or clean(model.get("surfboardmodeltypename"))
            or None
        )

        construction = (
            clean(detail.get("surfboardconstructiontype"))
            or clean(model.get("surfboardconstructiontype"))
            or None
        )

        fin_setup = normalise_fin_setup(
            clean(detail.get("finsystem")) + " " + clean(detail.get("finsystemoption"))
        )

        product_url = f"https://www.chillisurfboards.com/surfboards/detail.php?id={model_id}&direct=1&region=aus"

        for dimension in dimensions:
            length = extract_dimension_value(
                dimension,
                ["length_inches", "length", "length_display"],
            )
            width = extract_dimension_value(
                dimension,
                ["width_inches", "width_display", "width"],
            )
            thickness = extract_dimension_value(
                dimension,
                ["thickness_inches", "thickness_display", "thickness"],
            )
            volume = extract_dimension_value(
                dimension,
                ["volume", "volume_litres", "litres"],
            )

            if not length or not width or not thickness or not volume:
                failures.append({
                    "id_surfboardmodel": model_id,
                    "model_name": model_name,
                    "reason": "dimension row missing required field",
                    "dimension": dimension,
                })
                continue

            try:
                volume_litres = float(str(volume).replace("L", "").strip())
            except ValueError:
                failures.append({
                    "id_surfboardmodel": model_id,
                    "model_name": model_name,
                    "reason": "invalid volume",
                    "dimension": dimension,
                })
                continue

            rows.append({
                "brand": BRAND,
                "model_name": model_name,
                "model_family": model_name,
                "board_category": category,
                "description": clean(detail.get("description")) or None,
                "official_product_url": product_url,
                "official_image_url": first_image(detail),
                "recommended_wave_range": None,
                "recommended_surfer_weight": None,
                "length_feet_inches": clean(length).replace('"', ""),
                "width": clean(width).replace('"', ""),
                "thickness": clean(thickness).replace('"', ""),
                "volume_litres": volume_litres,
                "construction": construction,
                "fin_setup": fin_setup,
                "tail_shape": clean(detail.get("tailname")) or None,
                "source_product_title": model_name,
                "source_variant_title": f"{length} x {width} x {thickness} {volume_litres}L",
                "source": DETAIL_URL.format(id=model_id),
            })

        time.sleep(0.15)

    seen = set()
    deduped = []

    for row in rows:
        key = (
            row["model_name"].lower(),
            row["length_feet_inches"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
            row["construction"],
            row["fin_setup"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    deduped.sort(
        key=lambda row: (
            row["model_name"],
            row["construction"] or "",
            row["volume_litres"],
        )
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report = {
        "brand": BRAND,
        "source": MODELS_URL,
        "models_seen": len(models),
        "catalogue_rows": len(deduped),
        "models_with_rows": len(set(row["model_name"] for row in deduped)),
        "constructions": sorted(set(row["construction"] for row in deduped if row["construction"])),
        "failures": failures,
        "failure_count": len(failures),
        "output_file": str(OUTPUT_FILE),
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("=" * 100)
    print("CHILLI COMPLETE")
    print("=" * 100)
    print("Models seen:", len(models))
    print("Catalogue rows:", len(deduped))
    print("Models with rows:", report["models_with_rows"])
    print("Constructions:", report["constructions"])
    print("Failures:", len(failures))
    print("Output:", OUTPUT_FILE)
    print("Report:", REPORT_FILE)


if __name__ == "__main__":
    build_catalogue()
'''.strip() + "\n", encoding="utf-8")

print("Replaced Chilli builder with full official model catalogue version")
