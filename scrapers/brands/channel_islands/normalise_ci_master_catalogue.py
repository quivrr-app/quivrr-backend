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
    slug = str(item.get("slug") or "").strip()
    raw_name = str(item.get("model_name") or "").strip()
    raw_hint = str(item.get("raw_title_hint") or "").strip()

    if not hasattr(clean_model_name, "_display_name_map"):
        links_file = Path(__file__).resolve().parent / "output" / "ci_canonical_model_links.json"
        display_name_map = {}

        if links_file.exists():
            try:
                links = json.loads(links_file.read_text(encoding="utf-8"))
                for link in links:
                    link_slug = str(link.get("slug") or "").strip()
                    link_name = str(link.get("model_name") or "").strip()

                    if link_slug and link_name:
                        display_name_map[link_slug] = link_name
            except Exception:
                display_name_map = {}

        clean_model_name._display_name_map = display_name_map

    display_name_map = clean_model_name._display_name_map

    explicit_overrides = {
        "black-and-white": "Black/White",
        "ci-2-pro": "CI 2.Pro",
        "ci-2-pro-step-up": "CI Pro Step Up",
        "ci-pro-step-up": "CI Pro Step Up",
        "febs-fish": "Feb's Fish",
        "fishbeard": "Fish Beard",
        "happy-traveler-1": "Happy Traveler",
        "m-23": "M23",
        "mikey-february-shorty": "Mikey February Shorty",
        "pod-mod-1": "Pod Mod",
        "taco-grinder-1": "Taco Grinder",
        "the-black-beauty": "Black Beauty",
        "the-solution": "The Solution",
        "the-water-hog": "Waterhog",
        "tph-single-fin-1": "Tri Plane Hull",
        "ultra-joe-1": "Ultra Joe",
    }

    if slug in explicit_overrides:
        return explicit_overrides[slug]

    if slug in display_name_map:
        return display_name_map[slug]

    name = raw_name or raw_hint or slug

    if not name:
        return ""

    junk_titles = {
        "surfboard",
        "surfboards",
    }

    if name.lower() in junk_titles:
        name = slug

    if "-" in name and " " not in name:
        return name.replace("-", " ").title()

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
        "models_without_sizes": sum(1 for item in clean_catalogue if not item.get("sizes")),
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
