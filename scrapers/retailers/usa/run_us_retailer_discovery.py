from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.usa.normalise_us_retailer_inventory import main as normalise_main  # noqa: E402
from scrapers.retailers.usa.shopify.discover_us_shopify_products import (  # noqa: E402
    INPUT_FILE as SHOPIFY_INPUT,
    OUTPUT_FILE as SHOPIFY_OUTPUT,
    discover_target as discover_shopify_target,
)
from scrapers.retailers.usa.woocommerce.discover_us_woocommerce_products import (  # noqa: E402
    INPUT_FILE as WOOCOMMERCE_INPUT,
    OUTPUT_FILE as WOOCOMMERCE_OUTPUT,
    discover_target as discover_woocommerce_target,
)


OUTPUT_FILE = Path("scrapers/retailers/usa/output/us_discovery_orchestration_report.json")
SHOPIFY_TARGETS = {
    "surf_station",
    "jacks_surfboards",
    "real_watersports",
    "cleanline_surf",
    "hansen_surfboards",
    "hawaiian_south_shore",
    "encinitas_surfboards",
    "birds_surf_shed",
}
WOOCOMMERCE_TARGETS = set()

REGION_CODE = "US"
PRIORITY_TARGETS = {
    "surf_station",
    "jacks_surfboards",
    "catalyst_surf_shop",
    "ron_jon_surf_shop",
    "real_watersports",
    "cleanline_surf",
    "hansen_surfboards",
    "hawaiian_south_shore",
    "et_surf",
    "encinitas_surfboards",
    "birds_surf_shed",
    "froghouse_surf_shop",
}


def load_targets(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_us_target(target: dict, source: Path) -> None:
    region_code = target.get("regionCode")
    if region_code != REGION_CODE:
        raise RuntimeError(
            f"US discovery safety failed for {target.get('retailerSlug', '<missing>')} "
            f"in {source}: RegionCode must be 'US', got {region_code!r}."
        )


def write_platform_report(path: Path, platform: str, results: list[dict]) -> None:
    products = [product for result in results for product in result.get("products", [])]
    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "orchestrated_run",
        "purpose": f"US {platform} product discovery only. No SQL import or production table writes.",
        "targetsSelected": len(results),
        "results": [{key: value for key, value in result.items() if key != "products"} for result in results],
        "products": products,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def run_platform(
    *,
    name: str,
    input_file: Path,
    output_file: Path,
    discover,
    target_slugs: set[str] | None,
    max_pages: int,
    require_enabled: bool = True,
) -> dict:
    targets = load_targets(input_file)
    selected = [
        target
        for target in targets
        if (target.get("enabled") is True or not require_enabled)
        and (target_slugs is None or target.get("retailerSlug") in target_slugs)
    ]
    for target in selected:
        assert_us_target(target, input_file)
    results = [discover(target, max_pages) for target in selected]
    write_platform_report(output_file, name, results)
    return {
        "platform": name,
        "outputFile": str(output_file),
        "targets": [target["retailerSlug"] for target in selected],
        "productsAccepted": sum(result.get("productsAccepted", 0) for result in results),
        "productsRejected": sum(result.get("productsRejected", 0) for result in results),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run US retailer discovery adapters and generic normalisation without SQL writes."
    )
    parser.add_argument("--shopify-pages", type=int, default=0, help="Optional Shopify JSON page cap. Default 0 fetches until exhausted.")
    parser.add_argument("--woocommerce-pages", type=int, default=0, help="Optional WooCommerce page cap. Default 0 crawls until exhausted.")
    parser.add_argument("--dry-run", action="store_true", help="Validate Phase 1 US target metadata without network fetches or output writes.")
    args = parser.parse_args()

    if args.dry_run:
        configured = []
        for input_file in [SHOPIFY_INPUT, WOOCOMMERCE_INPUT]:
            for target in load_targets(input_file):
                assert_us_target(target, input_file)
                configured.append(target.get("retailerSlug"))
        known_targets = {
            target.get("retailerSlug")
            for target in load_targets(Path("scrapers/retailers/usa/us_retailer_targets.json"))
        }
        missing = sorted(PRIORITY_TARGETS - known_targets)
        if missing:
            raise RuntimeError(f"Missing priority US targets: {', '.join(missing)}")
        print("US retailer discovery dry-run complete")
        print(f"Priority targets validated: {', '.join(sorted(PRIORITY_TARGETS))}")
        print(f"Adapter targets configured: {', '.join(sorted(configured))}")
        return

    platform_reports = [
        run_platform(
            name="Shopify",
            input_file=SHOPIFY_INPUT,
            output_file=SHOPIFY_OUTPUT,
            discover=discover_shopify_target,
            target_slugs=SHOPIFY_TARGETS,
            max_pages=max(0, args.shopify_pages),
            require_enabled=True,
        ),
        run_platform(
            name="WooCommerce",
            input_file=WOOCOMMERCE_INPUT,
            output_file=WOOCOMMERCE_OUTPUT,
            discover=discover_woocommerce_target,
            target_slugs=WOOCOMMERCE_TARGETS if WOOCOMMERCE_TARGETS else None,
            max_pages=max(0, args.woocommerce_pages),
            require_enabled=True,
        ),
    ]

    original_argv = sys.argv[:]
    try:
        sys.argv = ["normalise_us_retailer_inventory.py"]
        normalise_main()
    finally:
        sys.argv = original_argv

    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "purpose": "US retailer discovery orchestration only. No SQL writes.",
        "normalisedOutputFile": "scrapers/retailers/usa/output/us_normalised_inventory.json",
        "platforms": platform_reports,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("US retailer discovery orchestration complete")
    for platform in platform_reports:
        print(
            f"{platform['platform']}: {platform['productsAccepted']} accepted, "
            f"{platform['productsRejected']} rejected"
        )
    print(f"Report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
