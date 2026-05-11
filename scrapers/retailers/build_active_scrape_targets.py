from pathlib import Path
import json
from urllib.parse import urlparse

INPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets_classified.json")
OUTPUT_FILE = Path("scrapers/retailers/active_scrape_targets.json")

SUPPORTED_PLATFORMS = {
    "Shopify",
    "WooCommerce",
    "BigCommerce",
    "Squarespace",
}


def normalise_website(url):
    if not url:
        return None

    parsed = urlparse(url)

    scheme = parsed.scheme or "https"
    host = parsed.netloc or parsed.path
    host = host.lower().strip()
    host = host.replace("www.", "")

    return f"{scheme}://{host}".rstrip("/")


def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    grouped = {}

    for retailer in retailers:
        platform = retailer.get("ecommerce_platform")

        if platform not in SUPPORTED_PLATFORMS:
            continue

        website_key = normalise_website(retailer.get("website"))

        if not website_key:
            continue

        if website_key not in grouped:
            grouped[website_key] = {
                "name": retailer.get("name"),
                "website": retailer.get("website"),
                "website_key": website_key,
                "country": retailer.get("country"),
                "platform": platform,
                "status": "active",
                "priority": retailer.get("priority", 1),
                "locations": [],
            }

        grouped[website_key]["locations"].append({
            "name": retailer.get("name"),
            "state": retailer.get("state"),
            "region_cluster": retailer.get("region_cluster"),
            "retailer_type": retailer.get("retailer_type"),
            "hardboards": retailer.get("hardboards"),
            "verification_status": retailer.get("verification_status"),
        })

    targets = sorted(
        grouped.values(),
        key=lambda x: (
            x["platform"],
            x["name"] or ""
        )
    )

    OUTPUT_FILE.write_text(
        json.dumps(targets, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nActive scrape targets built")
    print("=" * 60)
    print(f"Retailer records loaded: {len(retailers)}")
    print(f"Unique active scrape targets: {len(targets)}")

    platform_counts = {}

    for target in targets:
        platform_counts[target["platform"]] = platform_counts.get(target["platform"], 0) + 1

    print("\nBy platform:")

    for platform, count in sorted(platform_counts.items()):
        print(f"{platform}: {count}")

    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
    