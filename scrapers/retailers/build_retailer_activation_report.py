from pathlib import Path
import json
from collections import Counter
from urllib.parse import urlparse


INPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets_classified.json")
OUTPUT_FILE = Path("scrapers/retailers/retailer_activation_report.json")

SUPPORTED_PLATFORMS = {
    "shopify",
    "woocommerce",
}

EXCLUDED_RETAILER_TYPES = {
    "shaper_direct",
    "brand_direct",
    "marketplace_direct_shaper",
    "stockist_source",
    "manufacturer",
    "brand",
}

EXCLUDED_NAME_TERMS = {
    "js industries",
    "firewire",
    "slater designs",
    "lost surfboards",
    "mayhem",
    "pyzel",
    "channel islands",
    "ci surfboards",
    "haydenshapes",
    "dhd",
    "sharp eye",
    "sharpeye",
    "album",
    "christenson",
    "aipa",
    "chilli",
    "rusty",
    "pukas",
    "mctavish",
    "nsp",
    "walden",
    "dark arts",
}


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def normalise_platform(value):
    value = clean(value).lower()

    if value in {"shopify", "woocommerce"}:
        return value

    return ""


def normalise_website(url):
    url = clean(url)

    if not url:
        return ""

    parsed = urlparse(url)

    scheme = parsed.scheme or "https"
    host = parsed.netloc or parsed.path
    host = host.lower().strip()
    host = host.replace("www.", "")

    if not host:
        return ""

    return f"{scheme}://{host}".rstrip("/")


def retailer_name(record):
    return clean(
        record.get("primary_name")
        or record.get("name")
        or record.get("retailer_name")
    )


def is_manufacturer_or_brand(record):
    retailer_type = clean(record.get("retailer_type")).lower()

    if retailer_type in EXCLUDED_RETAILER_TYPES:
        return True

    retailer_types = record.get("retailer_types")

    if isinstance(retailer_types, list):
        for item in retailer_types:
            if clean(item).lower() in EXCLUDED_RETAILER_TYPES:
                return True

    name = retailer_name(record).lower()

    if name in EXCLUDED_NAME_TERMS:
        return True

    website = normalise_website(record.get("website")).lower()

    for term in EXCLUDED_NAME_TERMS:
        compact_term = term.replace(" ", "").replace("-", "")
        compact_site = website.replace(" ", "").replace("-", "")

        if compact_term and compact_term in compact_site:
            return True

    return False


def activation_status(record):
    country = clean(record.get("country")).lower()

    if country and country != "australia":
        return "excluded", "non_australian"

    if is_manufacturer_or_brand(record):
        return "excluded", "manufacturer_or_brand"

    if record.get("hardboards") is False:
        return "excluded", "not_hardboard_retailer"

    platform = normalise_platform(
        record.get("platform")
        or record.get("ecommerce_platform")
    )

    if not platform:
        return "excluded", "platform_unknown"

    if platform not in SUPPORTED_PLATFORMS:
        return "excluded", f"unsupported_platform_{platform}"

    website = normalise_website(record.get("website"))

    if not website:
        return "excluded", "missing_website"

    return "active", "supported_retailer"


def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    summary = Counter()
    activation = []

    for record in retailers:
        status, reason = activation_status(record)

        platform = normalise_platform(
            record.get("platform")
            or record.get("ecommerce_platform")
        )

        country = clean(record.get("country")) or "Australia"

        if country.lower() == "australia":
            summary["total_au"] += 1

        summary[f"status_{status}"] += 1
        summary[f"reason_{reason}"] += 1

        if platform:
            summary[f"platform_{platform}"] += 1
        else:
            summary["platform_unknown"] += 1

        activation.append({
            "name": retailer_name(record),
            "website": normalise_website(record.get("website")),
            "country": country,
            "platform": platform or "unknown",
            "retailer_type": clean(record.get("retailer_type")),
            "hardboards": record.get("hardboards"),
            "verification_status": clean(record.get("verification_status")),
            "status": status,
            "reason": reason,
            "priority": record.get("priority", 3),
        })

    activation = sorted(
        activation,
        key=lambda item: (
            item["status"] != "active",
            item["reason"],
            item["platform"],
            item["name"].lower(),
        ),
    )

    report = {
        "summary": dict(summary),
        "retailers": activation,
    }

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("Australian retailer activation report")
    print("=" * 60)

    for key, value in sorted(summary.items()):
        print(f"{key}: {value}")

    print("")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()