from pathlib import Path
import json
from collections import defaultdict

RAW_DIRS = [
    Path("scrapers/products/output/shopify"),
    Path("scrapers/products/output/woocommerce"),
]

LIKELY_FILE = Path("scrapers/products/output/likely_surfboards.json")
NORMALISED_FILE = Path("scrapers/products/output/normalised_surfboards.json")
OUTPUT_FILE = Path("scrapers/products/output/retailer_quality_report.json")


def load_json(path):
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            if isinstance(data.get("products"), list):
                return data["products"]

            if isinstance(data.get("items"), list):
                return data["items"]

        return []

    except Exception:
        return []


def retailer_name_from_file(path):
    return path.stem.replace("_", " ").title()


def has_value(item, key):
    value = item.get(key)
    return value is not None and str(value).strip() != ""


def main():
    raw_counts = {}

    for raw_dir in RAW_DIRS:
        if not raw_dir.exists():
            continue

        for file_path in raw_dir.glob("*.json"):
            retailer = retailer_name_from_file(file_path)
            raw_counts[retailer] = len(load_json(file_path))

    likely = load_json(LIKELY_FILE)
    normalised = load_json(NORMALISED_FILE)

    likely_by_retailer = defaultdict(int)
    normalised_by_retailer = defaultdict(list)

    for item in likely:
        retailer = item.get("retailer") or "Unknown"
        likely_by_retailer[retailer] += 1

    for item in normalised:
        retailer = item.get("retailer") or "Unknown"
        normalised_by_retailer[retailer].append(item)

    report = []

    all_retailers = sorted(
        set(raw_counts.keys()) |
        set(likely_by_retailer.keys()) |
        set(normalised_by_retailer.keys())
    )

    for retailer in all_retailers:
        raw_count = raw_counts.get(retailer, 0)
        likely_count = likely_by_retailer.get(retailer, 0)
        items = normalised_by_retailer.get(retailer, [])

        normalised_count = len(items)

        available_count = sum(
            1 for item in items
            if item.get("available") is True
        )

        length_count = sum(1 for item in items if has_value(item, "length"))
        volume_count = sum(1 for item in items if has_value(item, "volume_litres"))
        model_count = sum(1 for item in items if has_value(item, "model"))
        brand_count = sum(1 for item in items if has_value(item, "brand"))
        price_count = sum(1 for item in items if has_value(item, "price"))

        parse_score = 0

        if normalised_count:
            parse_score = round(
                (
                    (length_count / normalised_count) * 25 +
                    (volume_count / normalised_count) * 25 +
                    (model_count / normalised_count) * 20 +
                    (brand_count / normalised_count) * 15 +
                    (price_count / normalised_count) * 15
                ),
                2
            )

        if raw_count == 0:
            status = "no_raw_inventory"
        elif likely_count == 0:
            status = "needs_filter_or_scraper_review"
        elif parse_score >= 75:
            status = "strong"
        elif parse_score >= 45:
            status = "usable"
        else:
            status = "needs_parser_review"

        report.append({
            "retailer": retailer,
            "status": status,
            "raw_count": raw_count,
            "likely_surfboards": likely_count,
            "normalised_count": normalised_count,
            "available_count": available_count,
            "parse_score": parse_score,
            "fields": {
                "brand": brand_count,
                "model": model_count,
                "length": length_count,
                "volume_litres": volume_count,
                "price": price_count,
            }
        })

    report = sorted(
        report,
        key=lambda x: (
            x["status"] != "strong",
            x["status"] != "usable",
            -x["likely_surfboards"]
        )
    )

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nRetailer quality report built")
    print("=" * 60)

    status_counts = defaultdict(int)

    for row in report:
        status_counts[row["status"]] += 1

    for status, count in sorted(status_counts.items()):
        print(f"{status}: {count}")

    print("\nTop retailer quality:")
    for row in report[:20]:
        print(
            f"{row['retailer']} | "
            f"{row['status']} | "
            f"raw={row['raw_count']} | "
            f"likely={row['likely_surfboards']} | "
            f"score={row['parse_score']}"
        )

    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()