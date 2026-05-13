from pathlib import Path
import json
from collections import Counter
from urllib.parse import urlparse


INPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets_classified.json")
OUTPUT_FILE = Path("scrapers/retailers/active_scrape_targets.json")
REPORT_FILE = Path("scrapers/retailers/active_scrape_target_build_report.json")

SUPPORTED_PLATFORMS = {"shopify", "woocommerce"}

MANUFACTURER_OR_BRAND_TYPES = {
    "shaper_direct",
    "brand_direct",
    "marketplace_direct_shaper",
    "stockist_source",
    "manufacturer",
    "brand",
}


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def normalise_platform(value):
    value = clean(value).lower()

    if value in SUPPORTED_PLATFORMS:
        return value

    return value or "unknown"


def normalise_website(url):
    url = clean(url)

    if not url:
        return ""

    parsed = urlparse(url)

    if parsed.netloc:
        host = parsed.netloc
        scheme = parsed.scheme or "https"
    else:
        host = parsed.path
        scheme = "https"

    host = host.lower().strip().replace("www.", "")

    if not host:
        return ""

    return f"{scheme}://{host}".rstrip("/")


def first_list_value(record, key):
    value = record.get(key)

    if isinstance(value, list) and value:
        return clean(value[0])

    return clean(value)


def retailer_name(record):
    return (
        clean(record.get("primary_name"))
        or first_list_value(record, "retailer_names")
        or clean(record.get("name"))
        or clean(record.get("retailer_name"))
        or normalise_website(record.get("website"))
    )


def get_retailer_types(record):
    values = []

    retailer_type = clean(record.get("retailer_type")).lower()

    if retailer_type:
        values.append(retailer_type)

    retailer_types = record.get("retailer_types")

    if isinstance(retailer_types, list):
        values.extend(clean(item).lower() for item in retailer_types if clean(item))

    return values


def is_manufacturer_or_brand(record):
    retailer_types = get_retailer_types(record)

    return any(item in MANUFACTURER_OR_BRAND_TYPES for item in retailer_types)


def get_exclusion_reason(record):
    country = clean(record.get("country")).lower()

    if country and country != "australia":
        return "non_australian"

    if is_manufacturer_or_brand(record):
        return "manufacturer_or_brand"

    if record.get("hardboards") is False:
        return "not_hardboard_retailer"

    platform = normalise_platform(record.get("platform") or record.get("ecommerce_platform"))

    if platform not in SUPPORTED_PLATFORMS:
        return f"unsupported_platform_{platform}"

    website = normalise_website(record.get("website"))

    if not website:
        return "missing_website"

    return ""


def build_target(record):
    website = normalise_website(record.get("website"))
    platform = normalise_platform(record.get("platform") or record.get("ecommerce_platform"))

    return {
        "primary_name": retailer_name(record),
        "website": website,
        "website_key": website,
        "country": clean(record.get("country")) or "Australia",
        "platform": platform,
        "status": "active",
        "priority": record.get("priority", 3),
        "locations": [],
        "source": "retailer_scrape_targets_classified",
    }


def build_location(record):
    return {
        "name": retailer_name(record),
        "states": record.get("states", []),
        "region_clusters": record.get("region_clusters", []),
        "retailer_types": record.get("retailer_types", []),
        "hardboards": record.get("hardboards"),
        "verification_statuses": record.get("verification_statuses", []),
    }


def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    grouped = {}
    excluded = []
    reasons = Counter()
    platforms = Counter()

    for record in retailers:
        platform = normalise_platform(record.get("platform") or record.get("ecommerce_platform"))
        platforms[platform] += 1

        reason = get_exclusion_reason(record)

        if reason:
            reasons[reason] += 1
            excluded.append({
                "name": retailer_name(record),
                "website": normalise_website(record.get("website")),
                "platform": platform,
                "reason": reason,
            })
            continue

        website_key = normalise_website(record.get("website"))

        if website_key not in grouped:
            grouped[website_key] = build_target(record)

        grouped[website_key]["locations"].append(build_location(record))

        grouped[website_key]["priority"] = min(
            grouped[website_key].get("priority", 3),
            record.get("priority", 3),
        )

    targets = sorted(
        grouped.values(),
        key=lambda item: (
            item.get("platform", ""),
            item.get("primary_name", "").lower(),
        ),
    )

    OUTPUT_FILE.write_text(
        json.dumps(targets, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    REPORT_FILE.write_text(
        json.dumps(
            {
                "total_records": len(retailers),
                "active_targets": len(targets),
                "excluded_records": len(excluded),
                "platforms_seen": dict(platforms),
                "exclusion_reasons": dict(reasons),
                "excluded": excluded,
                "active": targets,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("Active scrape targets built")
    print("=" * 60)
    print(f"Retailer records loaded: {len(retailers)}")
    print(f"Unique active retailer targets: {len(targets)}")
    print(f"Excluded records: {len(excluded)}")

    print("")
    print("Platforms seen:")

    for platform, count in sorted(platforms.items()):
        print(f"{platform}: {count}")

    print("")
    print("Exclusion reasons:")

    for reason, count in sorted(reasons.items()):
        print(f"{reason}: {count}")

    print("")
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()