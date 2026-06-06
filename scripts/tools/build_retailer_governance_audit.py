import csv
import json
from pathlib import Path


ACTIVE_TARGETS = Path("scrapers/retailers/active_scrape_targets.json")
HEALTH_REPORT = Path("scrapers/products/output/retailer_scrape_health.json")
OUTPUT_JSON = Path("scrapers/products/output/retailer_governance_audit.json")
OUTPUT_CSV = Path("scrapers/products/output/retailer_governance_audit.csv")


BUSINESS_DISABLED = {
    "awsm_surf": "Clothing/apparel store, not suitable for Quivrr hardboard retailer inventory",
    "beaches_apparel": "Clothing/apparel store, not suitable for Quivrr hardboard retailer inventory",
    "board_hub": "Not a surfboard retailer, removed from Quivrr hardboard inventory scope",
    "board_store": "Skateboards only, not suitable for Quivrr hardboard retailer inventory",
    "boardriders_coolangatta": "Domain unavailable, removed from active retailer inventory scope",
    "cordingleys_surf": "No online surfboard inventory available for automated Quivrr search",
    "cronulla_surf_design": "Clothing/accessories store, not suitable for Quivrr hardboard retailer inventory",
    "empire_ave": "Not a surfboard retailer, removed from Quivrr hardboard inventory scope",
    "full_circle_surf": "Domain unavailable, removed from active retailer inventory scope",
    "goodtime_surfboards": "Does not stock supported Quivrr surfboard brands",
    "island_surfboards": "Independent shaper not supported by current Quivrr catalogue",
    "manly_surf_guide_surfboard_outlet": "Not selling supported online surfboard inventory",
    "mid_coast_surf": "Domain unavailable, removed from active retailer inventory scope",
    "ocean_and_earth": "Brand/accessory store, not suitable for Quivrr hardboard retailer inventory",
    "red_herring_surf": "Redirects to Board Collective, removed to avoid duplicate retailer coverage",
    "rip_curl_australia": "Does not sell hardboard surfboard inventory online for Quivrr search",
    "saltwater_wine_port_macquarie": "Clothing/apparel store, not suitable for Quivrr hardboard retailer inventory",
    "surf_boardroom": "No online surfboard inventory available for automated Quivrr search",
    "surf_warehouse": "Domain for sale, removed from active retailer inventory scope",
    "underground_surf": "No online surfboard inventory available for automated Quivrr search",
    "yallingup_surf_shop": "Domain unavailable, removed from active retailer inventory scope",
}



RETAILER_ALIASES = {
    "coopers_board_store_raw_inventory": "coopers_board_store",
    "coopers_debug_inventory": "coopers_board_store",
    "coopers_test_inventory": "coopers_board_store",
    "cordingleys_surf": "cordingleys_surf",
    "cordingley_s_surf": "cordingleys_surf",
    "cordingley's_surf": "cordingleys_surf",
    "surf_fx": "surf_fx",
    "surf_fx_": "surf_fx",
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
        .replace(".", "")
        .replace(" ", "_")
    )


def canonical_slug(value):
    slug = make_slug(value)
    return RETAILER_ALIASES.get(slug, slug)


def title_from_slug(slug):
    return slug.replace("_", " ").title()


def load_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def classify(row):
    slug = row["retailer_slug"]
    health = row["health"]
    raw = row["raw_products"]
    verified = row["verified_surfboards"]
    available = row["available_inventory"]

    if slug in BUSINESS_DISABLED:
        return "business_disabled", BUSINESS_DISABLED[slug]

    if available > 0 and verified > 0:
        return "production", "Producing available surfboard inventory"

    if verified > 0 and available == 0:
        return "stock_status_review", "Surfboards identified but no available inventory"

    if raw > 0 and verified == 0:
        return "parser_review", "Products scraped but surfboard filter did not identify boards"

    if raw == 0:
        return "endpoint_review", "No raw products returned from scrape output"

    if health in ("failed", "poor"):
        return "technical_review", "Unhealthy scrape result"

    return "review", "Needs manual review"


def main():
    active_targets = load_json(ACTIVE_TARGETS) or []
    health_report = load_json(HEALTH_REPORT) or {}
    health_rows = health_report.get("retailers", [])

    active_by_slug = {}
    for item in active_targets:
        slug = canonical_slug(item.get("primary_name"))
        active_by_slug[slug] = item

    merged = {}

    for row in health_rows:
        source_slug = canonical_slug(row.get("retailer_slug") or row.get("retailer_name"))
        existing = merged.get(source_slug)

        if not existing:
            merged[source_slug] = {
                "retailer_slug": source_slug,
                "retailer_name": title_from_slug(source_slug),
                "platforms": set(),
                "raw_products": 0,
                "verified_surfboards": 0,
                "available_inventory": 0,
                "normalised_inventory": 0,
                "duplicate_candidates": 0,
                "source_rows": [],
                "health_values": [],
                "statuses": [],
            }

        item = merged[source_slug]
        platform = clean(row.get("platform")) or "unknown"
        item["platforms"].add(platform)
        item["raw_products"] += int(row.get("raw_products") or 0)
        item["verified_surfboards"] += int(row.get("verified_surfboards") or 0)
        item["available_inventory"] += int(row.get("available_inventory") or 0)
        item["normalised_inventory"] += int(row.get("normalised_inventory") or 0)
        item["duplicate_candidates"] += int(row.get("duplicate_candidates") or 0)
        item["source_rows"].append(row.get("retailer_name"))
        item["health_values"].append(row.get("health"))
        item["statuses"].append(row.get("status"))

    for slug, target in active_by_slug.items():
        if slug not in merged:
            merged[slug] = {
                "retailer_slug": slug,
                "retailer_name": clean(target.get("primary_name")) or title_from_slug(slug),
                "platforms": {clean(target.get("platform")) or "unknown"},
                "raw_products": 0,
                "verified_surfboards": 0,
                "available_inventory": 0,
                "normalised_inventory": 0,
                "duplicate_candidates": 0,
                "source_rows": [],
                "health_values": ["missing"],
                "statuses": ["missing_from_health"],
            }

    output_rows = []

    for slug, item in merged.items():
        target = active_by_slug.get(slug, {})
        platform_list = sorted([p for p in item["platforms"] if p])
        health_values = [h for h in item["health_values"] if h]
        statuses = [s for s in item["statuses"] if s]

        if item["available_inventory"] > 0:
            health = "good"
        elif "failed" in health_values:
            health = "failed"
        elif "poor" in health_values:
            health = "poor"
        elif "warning" in health_values:
            health = "warning"
        elif "fair" in health_values:
            health = "fair"
        elif "missing" in health_values:
            health = "missing"
        else:
            health = "unknown"

        base_row = {
            "retailer_slug": slug,
            "retailer_name": clean(target.get("primary_name")) or item["retailer_name"],
            "website": clean(target.get("website")),
            "platform": ", ".join(platform_list),
            "raw_products": item["raw_products"],
            "verified_surfboards": item["verified_surfboards"],
            "available_inventory": item["available_inventory"],
            "normalised_inventory": item["normalised_inventory"],
            "duplicate_candidates": item["duplicate_candidates"],
            "health": health,
            "source_rows": sorted(set([clean(v) for v in item["source_rows"] if clean(v)])),
            "statuses": sorted(set([clean(v) for v in statuses if clean(v)])),
            "active_target": slug in active_by_slug,
        }

        classification, reason = classify(base_row)
        base_row["governance_status"] = classification
        base_row["governance_reason"] = reason
        base_row["approved_logo_file"] = f"{slug}.png" if classification == "production" else ""

        output_rows.append(base_row)

    output_rows = sorted(
        output_rows,
        key=lambda row: (
            row["governance_status"],
            -row["available_inventory"],
            row["retailer_name"],
        ),
    )

    summary = {}
    for row in output_rows:
        summary[row["governance_status"]] = summary.get(row["governance_status"], 0) + 1

    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "summary": summary,
                "retailers": output_rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "retailer_slug",
            "retailer_name",
            "website",
            "platform",
            "governance_status",
            "governance_reason",
            "raw_products",
            "verified_surfboards",
            "available_inventory",
            "normalised_inventory",
            "duplicate_candidates",
            "health",
            "active_target",
            "approved_logo_file",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in output_rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    print("")
    print("Retailer governance audit")
    print("=" * 70)

    for key, value in sorted(summary.items()):
        print(f"{key}: {value}")

    print("")
    print("Production retailers by available inventory")
    for row in [r for r in output_rows if r["governance_status"] == "production"][:30]:
        print(
            f"- {row['retailer_name']} | "
            f"{row['available_inventory']} available | "
            f"{row['platform']} | "
            f"{row['approved_logo_file']}"
        )

    print("")
    print("Review and disabled retailers")
    for row in [r for r in output_rows if r["governance_status"] != "production"]:
        print(
            f"- {row['retailer_name']} | "
            f"{row['governance_status']} | "
            f"{row['raw_products']} raw | "
            f"{row['verified_surfboards']} verified | "
            f"{row['available_inventory']} available | "
            f"{row['governance_reason']}"
        )

    print("")
    print(f"Saved JSON: {OUTPUT_JSON}")
    print(f"Saved CSV : {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
