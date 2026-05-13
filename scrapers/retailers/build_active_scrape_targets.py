from pathlib import Path
import json
from collections import Counter
from urllib.parse import urlparse


INPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets_classified.json")
EXPANSION_FILE = Path("scrapers/retailers/retailer_expansion_candidates_au.json")

DETECTION_REPORT = Path(
    "scrapers/retailers/retailer_platform_detection_report.json"
)

OUTPUT_FILE = Path("scrapers/retailers/active_scrape_targets.json")

REPORT_FILE = Path(
    "scrapers/retailers/active_scrape_target_build_report.json"
)

SUPPORTED_PLATFORMS = {
    "shopify",
    "woocommerce",
    "bigcommerce",
    "magento",
    "neto_maropost",
    "squarespace",
    "wix",
    "ecwid",
}

MANUFACTURER_OR_BRAND_TYPES = {
    "shaper_direct",
    "brand_direct",
    "marketplace_direct_shaper",
    "stockist_source",
    "manufacturer",
    "brand",
}

EXCLUDED_RETAILERS = {
    "js industries",
    "ocean & earth store",
}


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def normalise_platform(value):
    value = clean(value).lower()

    platform_aliases = {
        "neto": "neto_maropost",
        "maropost": "neto_maropost",
        "maropost commerce cloud": "neto_maropost",
        "big commerce": "bigcommerce",
        "woo commerce": "woocommerce",
        "woo": "woocommerce",
        "wix stores": "wix",
        "squarespace commerce": "squarespace",
    }

    return platform_aliases.get(value, value or "unknown")


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
        values.extend(
            clean(item).lower()
            for item in retailer_types
            if clean(item)
        )

    return values


def is_manufacturer_or_brand(record):
    retailer_types = get_retailer_types(record)

    return any(
        item in MANUFACTURER_OR_BRAND_TYPES
        for item in retailer_types
    )


def load_retailers():
    retailers = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    if EXPANSION_FILE.exists():
        retailers.extend(
            json.loads(
                EXPANSION_FILE.read_text(encoding="utf-8")
            )
        )

    return retailers


def load_detection_overrides():
    overrides = {}

    if not DETECTION_REPORT.exists():
        return overrides

    report = json.loads(
        DETECTION_REPORT.read_text(encoding="utf-8")
    )

    for result in report.get("results", []):
        website = normalise_website(result.get("website"))

        if not website:
            continue

        overrides[website] = {
            "platform": normalise_platform(
                result.get("detected_platform")
            ),
            "status": clean(result.get("status")).lower(),
        }

    return overrides


def get_detection_override(record, overrides):
    website = normalise_website(record.get("website"))

    return overrides.get(website)


def get_platform(record, overrides):
    override = get_detection_override(record, overrides)

    if override:
        platform = override.get("platform")

        if platform:
            return normalise_platform(platform)

    return normalise_platform(
        record.get("platform")
        or record.get("ecommerce_platform")
    )


def get_exclusion_reason(record, overrides):
    country = clean(record.get("country")).lower()

    if country and country != "australia":
        return "non_australian"

    name = retailer_name(record).lower()

    if name in EXCLUDED_RETAILERS:
        return "excluded_retailer"

    if is_manufacturer_or_brand(record):
        return "manufacturer_or_brand"

    if record.get("hardboards") is False:
        return "not_hardboard_retailer"

    platform = get_platform(record, overrides)

    if platform not in SUPPORTED_PLATFORMS:
        return f"unsupported_platform_{platform}"

    website = normalise_website(record.get("website"))

    if not website:
        return "missing_website"

    return ""


def build_target(record, overrides):
    website = normalise_website(record.get("website"))
    platform = get_platform(record, overrides)

    return {
        "primary_name": retailer_name(record),
        "website": website,
        "website_key": website,
        "country": clean(record.get("country")) or "Australia",
        "platform": platform,
        "status": "active",
        "priority": record.get("priority", 3),
        "locations": [],
        "source": "retailer_detection_pipeline",
    }


def build_location(record):
    return {
        "name": retailer_name(record),
        "states": record.get("states", []),
        "region_clusters": record.get("region_clusters", []),
        "retailer_types": record.get("retailer_types", []),
        "hardboards": record.get("hardboards"),
        "verification_statuses": record.get(
            "verification_statuses",
            []
        ),
    }


def main():
    retailers = load_retailers()
    detection_overrides = load_detection_overrides()

    grouped = {}
    excluded = []
    reasons = Counter()
    platforms = Counter()

    for record in retailers:
        platform = get_platform(
            record,
            detection_overrides,
        )

        platforms[platform] += 1

        reason = get_exclusion_reason(
            record,
            detection_overrides,
        )

        if reason:
            reasons[reason] += 1

            excluded.append({
                "name": retailer_name(record),
                "website": normalise_website(
                    record.get("website")
                ),
                "platform": platform,
                "reason": reason,
            })

            continue

        website_key = normalise_website(
            record.get("website")
        )

        if website_key not in grouped:
            grouped[website_key] = build_target(
                record,
                detection_overrides,
            )

        grouped[website_key]["locations"].append(
            build_location(record)
        )

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
        json.dumps(
            targets,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    REPORT_FILE.write_text(
        json.dumps(
            {
                "total_records": len(retailers),
                "supported_platforms": sorted(SUPPORTED_PLATFORMS),
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
    print("Supported platforms:")

    for platform in sorted(SUPPORTED_PLATFORMS):
        print(platform)

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