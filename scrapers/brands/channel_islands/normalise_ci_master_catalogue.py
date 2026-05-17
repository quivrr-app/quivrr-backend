import json
from pathlib import Path


INPUT_FILE = Path("scrapers/brands/channel_islands/output/ci_master_catalogue.json")
OUTPUT_FILE = Path("scrapers/brands/channel_islands/output/ci_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/channel_islands/output/ci_master_catalogue_clean_report.json")


CONSTRUCTION_MAP = {
    "ECT": "ECT-Carbon",
    "Carbon": "ECT-Carbon",
    "Spine-Tek": "Spine-Tek",
    "PU": "PU",
    "PE": "PE",
    "Poly": "PE",
    "Epoxy": "Spine-Tek",
    "EPS": "Spine-Tek",
}


def normalise_constructions(values):
    clean = []

    for value in values or []:
        mapped = CONSTRUCTION_MAP.get(value)

        if mapped and mapped not in clean:
            clean.append(mapped)

    if not clean:
        clean.append("PU")

    return clean


def dedupe_sizes(sizes):
    clean = []
    seen = set()

    for size in sizes or []:
        key = (
            size.get("length"),
            size.get("width"),
            size.get("thickness"),
            size.get("volume_litres"),
        )

        if key in seen:
            continue

        seen.add(key)
        clean.append(size)

    return clean


def clean_model_name(item):
    name = item.get("model_name") or item.get("raw_title_hint") or item.get("slug")

    if not name:
        return ""

    name = str(name).strip()

    junk_titles = {
        "channel islands surfboards",
        "board models",
        "surfboards",
    }

    if name.lower() in junk_titles:
        return str(item.get("slug", "")).replace("-", " ").title()

    return name


def main():
    catalogue = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    clean_catalogue = []
    removed = []
    seen_slugs = set()

    for item in catalogue:
        slug = item.get("slug")
        model_name = clean_model_name(item)

        sizes = dedupe_sizes(item.get("sizes"))

        if not sizes:
            removed.append({
                "slug": slug,
                "model_name": model_name,
                "reason": "no active stock dimensions",
            })
            continue

        if slug in seen_slugs:
            removed.append({
                "slug": slug,
                "model_name": model_name,
                "reason": "duplicate slug",
            })
            continue

        seen_slugs.add(slug)

        clean_catalogue.append({
            **item,
            "model_name": model_name,
            "constructions": normalise_constructions(item.get("constructions")),
            "sizes": sizes,
        })

    OUTPUT_FILE.write_text(
        json.dumps(clean_catalogue, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report = {
        "input_models": len(catalogue),
        "clean_models": len(clean_catalogue),
        "removed_models": len(removed),
        "total_sizes": sum(len(item["sizes"]) for item in clean_catalogue),
        "removed": removed,
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("CI clean catalogue complete")
    print(f"Input models: {report['input_models']}")
    print(f"Clean models: {report['clean_models']}")
    print(f"Removed models: {report['removed_models']}")
    print(f"Total sizes: {report['total_sizes']}")
    print(OUTPUT_FILE)
    print(REPORT_FILE)


if __name__ == "__main__":
    main()
