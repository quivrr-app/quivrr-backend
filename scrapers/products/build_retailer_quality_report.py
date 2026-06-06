import json
from collections import defaultdict
from pathlib import Path


OUTPUT_ROOT = Path("scrapers/products/output")

SCRAPE_SOURCES = [
    ("shopify", OUTPUT_ROOT / "shopify"),
    ("woocommerce", OUTPUT_ROOT / "woocommerce"),
    ("bigcommerce", OUTPUT_ROOT / "bigcommerce"),
    ("magento", OUTPUT_ROOT / "magento"),
    ("neto_maropost", OUTPUT_ROOT / "neto_maropost"),
    ("squarespace", OUTPUT_ROOT / "squarespace"),
    ("ecwid", OUTPUT_ROOT / "ecwid"),
    ("coopers", OUTPUT_ROOT / "coopers"),
]

LIKELY_SURFBOARDS_FILE = OUTPUT_ROOT / "likely_surfboards.json"
NORMALISED_FILE = OUTPUT_ROOT / "normalised_surfboards.json"
OUTPUT_FILE = OUTPUT_ROOT / "retailer_scrape_health.json"

EXCLUDED_NON_BOARD_RETAILERS = {
    "surf_dive_n_ski",
    "rip_curl_australia",
    "ocean_and_earth",
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def make_slug(value):
    return (
        clean(value)
        .lower()
        .replace("&", "and")
        .replace("'", "")
        .replace("’", "")
        .replace("-", "_")
        .replace("/", "_")
        .replace(" ", "_")
    )


def retailer_slug_to_name(slug):
    return slug.replace("_", " ").title()


def load_json(path):
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for key in ["products", "items", "data", "results"]:
                if isinstance(data.get(key), list):
                    return data[key]

        return []
    except Exception:
        return []


def collect_raw_counts():
    retailer_stats = {}

    for platform, directory in SCRAPE_SOURCES:
        if not directory.exists():
            continue

        for file_path in directory.glob("*.json"):
            retailer_slug = file_path.stem

            if retailer_slug in EXCLUDED_NON_BOARD_RETAILERS:
                continue

            retailer_name = retailer_slug_to_name(retailer_slug)
            raw_products = load_json(file_path)

            retailer_stats[retailer_slug] = {
                "retailer_slug": retailer_slug,
                "retailer_name": retailer_name,
                "platform": platform,
                "raw_products": len(raw_products),
                "verified_surfboards": 0,
                "available_inventory": 0,
                "normalised_inventory": 0,
                "duplicate_candidates": 0,
                "status": "success",
                "notes": [],
            }

            if len(raw_products) == 0:
                retailer_stats[retailer_slug]["status"] = "empty_scrape"
                retailer_stats[retailer_slug]["notes"].append(
                    "No products returned from retailer scrape"
                )

    return retailer_stats


def add_verified_counts(retailer_stats):
    likely_surfboards = load_json(LIKELY_SURFBOARDS_FILE)

    for item in likely_surfboards:
        retailer = clean(item.get("retailer"))

        if not retailer:
            continue

        retailer_slug = make_slug(retailer)

        if retailer_slug in EXCLUDED_NON_BOARD_RETAILERS:
            continue

        if retailer_slug not in retailer_stats:
            retailer_stats[retailer_slug] = {
                "retailer_slug": retailer_slug,
                "retailer_name": retailer,
                "platform": "unknown",
                "raw_products": 0,
                "verified_surfboards": 0,
                "available_inventory": 0,
                "normalised_inventory": 0,
                "duplicate_candidates": 0,
                "status": "unknown",
                "notes": [],
            }

        retailer_stats[retailer_slug]["verified_surfboards"] += 1

        if item.get("available") is True:
            retailer_stats[retailer_slug]["available_inventory"] += 1


def add_normalised_counts(retailer_stats):
    normalised = load_json(NORMALISED_FILE)
    dedupe_tracker = defaultdict(set)

    for item in normalised:
        retailer = clean(item.get("retailer"))

        if not retailer:
            continue

        retailer_slug = make_slug(retailer)

        if retailer_slug not in retailer_stats:
            continue

        retailer_stats[retailer_slug]["normalised_inventory"] += 1

        dedupe_key = "|".join([
            clean(item.get("product_url")).lower(),
            clean(item.get("title")).lower(),
            clean(item.get("length")).lower(),
            str(item.get("volume_litres") or ""),
            str(item.get("price") or ""),
        ])

        if dedupe_key in dedupe_tracker[retailer_slug]:
            retailer_stats[retailer_slug]["duplicate_candidates"] += 1
        else:
            dedupe_tracker[retailer_slug].add(dedupe_key)


def classify_health(retailer_stats):
    for retailer in retailer_stats.values():
        raw_products = retailer["raw_products"]
        verified = retailer["verified_surfboards"]
        available = retailer["available_inventory"]

        if raw_products == 0:
            retailer["health"] = "failed"
            continue

        if verified == 0:
            retailer["health"] = "poor"
            retailer["notes"].append(
                "Products scraped but no surfboards identified"
            )
            continue

        if available == 0:
            retailer["health"] = "poor"
            retailer["notes"].append(
                "Surfboards identified but no available inventory"
            )
            continue

        surfboard_ratio = verified / raw_products

        if surfboard_ratio < 0.02:
            retailer["health"] = "warning"
            retailer["notes"].append(
                "Very low surfboard extraction ratio"
            )
        elif surfboard_ratio < 0.08:
            retailer["health"] = "fair"
        else:
            retailer["health"] = "good"


def build_summary(retailer_stats):
    summary = {
        "total_retailers": len(retailer_stats),
        "good": 0,
        "fair": 0,
        "warning": 0,
        "poor": 0,
        "failed": 0,
        "total_raw_products": 0,
        "total_verified_surfboards": 0,
        "total_available_inventory": 0,
        "total_duplicate_candidates": 0,
    }

    for retailer in retailer_stats.values():
        health = retailer.get("health", "unknown")

        if health in summary:
            summary[health] += 1

        summary["total_raw_products"] += retailer["raw_products"]
        summary["total_verified_surfboards"] += retailer["verified_surfboards"]
        summary["total_available_inventory"] += retailer["available_inventory"]
        summary["total_duplicate_candidates"] += retailer["duplicate_candidates"]

    return summary


def main():
    retailer_stats = collect_raw_counts()

    add_verified_counts(retailer_stats)
    add_normalised_counts(retailer_stats)
    classify_health(retailer_stats)

    ordered = sorted(
        retailer_stats.values(),
        key=lambda item: (
            item.get("health", ""),
            -item.get("available_inventory", 0),
            item.get("retailer_name", ""),
        ),
    )

    report = {
        "summary": build_summary(retailer_stats),
        "retailers": ordered,
        "excluded_non_board_retailers": sorted(EXCLUDED_NON_BOARD_RETAILERS),
    }

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("Retailer scrape health report")
    print("=" * 60)

    for key, value in report["summary"].items():
        print(f"{key}: {value}")

    print("")
    print("Top retailers by available inventory")

    top = sorted(
        ordered,
        key=lambda item: item.get("available_inventory", 0),
        reverse=True,
    )[:20]

    for retailer in top:
        print(
            f"- {retailer['retailer_name']} | "
            f"{retailer['available_inventory']} available | "
            f"{retailer['health']} | "
            f"{retailer['platform']}"
        )

    print("")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
