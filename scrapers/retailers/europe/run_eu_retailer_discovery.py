from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.europe.custom.discover_eu_custom_products import (  # noqa: E402
    INPUT_FILE as CUSTOM_INPUT,
    OUTPUT_FILE as CUSTOM_OUTPUT,
    discover_target as discover_custom_target,
)
from scrapers.retailers.europe.magento.discover_eu_magento_products import (  # noqa: E402
    INPUT_FILE as MAGENTO_INPUT,
    OUTPUT_FILE as MAGENTO_OUTPUT,
    discover_target as discover_magento_target,
)
from scrapers.retailers.europe.normalise_eu_retailer_inventory import (  # noqa: E402
    main as normalise_main,
)
from scrapers.retailers.europe.prestashop.discover_eu_prestashop_products import (  # noqa: E402
    INPUT_FILE as PRESTASHOP_INPUT,
    OUTPUT_FILE as PRESTASHOP_OUTPUT,
    discover_target as discover_prestashop_target,
)
from scrapers.retailers.europe.shopify.discover_eu_shopify_products import (  # noqa: E402
    INPUT_FILE as SHOPIFY_INPUT,
    OUTPUT_FILE as SHOPIFY_OUTPUT,
    discover_target as discover_shopify_target,
)
from scrapers.retailers.europe.woocommerce.discover_eu_woocommerce_products import (  # noqa: E402
    INPUT_FILE as WOOCOMMERCE_INPUT,
    OUTPUT_FILE as WOOCOMMERCE_OUTPUT,
    discover_target as discover_woocommerce_target,
)


OUTPUT_FILE = Path("scrapers/retailers/europe/output/eu_discovery_orchestration_report.json")

SHOPIFY_TARGETS = {
    "pukas_surf_shop",
    "bell_surf",
    "board_exchange",
    "pop_up_surf_shop",
    "noordzee_boardstore",
    "gsi_europe",
    "hart_beach",
}
PRESTASHOP_TARGETS = {"mundo_surf", "single_quiver"}
CUSTOM_TARGETS = {"surf_corner", "tablas_surf_shop"}
WOOCOMMERCE_TARGETS = {"surf_boss"}

REGION_CODE = "EU"
ROLLOUT_TARGETS = {
    "bell_surf",
    "board_exchange",
    "gsi_europe",
    "mundo_surf",
    "noordzee_boardstore",
    "pop_up_surf_shop",
    "single_quiver",
    "surf_boss",
    "surf_corner",
    "tablas_surf_shop",
    "hart_beach",
}
PRIORITY_TARGETS = {"58_surf", "pukas_surf_shop", *ROLLOUT_TARGETS}


def load_targets(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_eu_target(target: dict, source: Path) -> None:
    region_code = target.get("regionCode")
    if region_code != REGION_CODE:
        raise RuntimeError(
            f"EU discovery safety failed for {target.get('retailerSlug', '<missing>')} "
            f"in {source}: RegionCode must be 'EU', got {region_code!r}."
        )


def write_platform_report(path: Path, platform: str, results: list[dict]) -> None:
    products = [
        product
        for result in results
        for product in result.get("products", [])
    ]
    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "orchestrated_run",
        "purpose": f"EU {platform} product discovery only. No SQL import or production table writes.",
        "targetsSelected": len(results),
        "results": [
            {key: value for key, value in result.items() if key != "products"}
            for result in results
        ],
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
        assert_eu_target(target, input_file)
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
        description="Run EU retailer discovery adapters and generic normalisation without SQL writes."
    )
    parser.add_argument(
        "--magento-pages",
        type=int,
        default=0,
        help="Optional 58 Surf category page cap. Default 0 fetches until exhausted.",
    )
    parser.add_argument(
        "--shopify-pages",
        type=int,
        default=0,
        help="Optional Shopify JSON page cap. Default 0 fetches until exhausted.",
    )
    parser.add_argument("--prestashop-pages", type=int, default=0, help="0 crawls until exhausted.")
    parser.add_argument("--custom-pages", type=int, default=0, help="0 crawls until exhausted.")
    parser.add_argument("--woocommerce-pages", type=int, default=0, help="0 crawls until exhausted.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate priority EU target metadata without network fetches or output writes.",
    )
    args = parser.parse_args()

    if args.dry_run:
        configured = []
        for input_file in [
            SHOPIFY_INPUT,
            MAGENTO_INPUT,
            WOOCOMMERCE_INPUT,
            PRESTASHOP_INPUT,
            CUSTOM_INPUT,
        ]:
            for target in load_targets(input_file):
                if target.get("retailerSlug") in PRIORITY_TARGETS:
                    assert_eu_target(target, input_file)
                    configured.append(target.get("retailerSlug"))
        missing = sorted(PRIORITY_TARGETS - set(configured))
        if missing:
            raise RuntimeError(f"Missing priority EU targets: {', '.join(missing)}")
        print("EU retailer discovery dry-run complete")
        print(f"Priority targets validated: {', '.join(sorted(configured))}")
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
            name="Magento/html",
            input_file=MAGENTO_INPUT,
            output_file=MAGENTO_OUTPUT,
            discover=discover_magento_target,
            target_slugs=None,
            max_pages=max(0, args.magento_pages),
        ),
        run_platform(
            name="PrestaShop",
            input_file=PRESTASHOP_INPUT,
            output_file=PRESTASHOP_OUTPUT,
            discover=discover_prestashop_target,
            target_slugs=PRESTASHOP_TARGETS,
            max_pages=max(0, args.prestashop_pages),
        ),
        run_platform(
            name="Structured/custom",
            input_file=CUSTOM_INPUT,
            output_file=CUSTOM_OUTPUT,
            discover=lambda target, pages: discover_custom_target(target, pages),
            target_slugs=CUSTOM_TARGETS,
            max_pages=max(0, args.custom_pages),
        ),
        run_platform(
            name="WooCommerce",
            input_file=WOOCOMMERCE_INPUT,
            output_file=WOOCOMMERCE_OUTPUT,
            discover=discover_woocommerce_target,
            target_slugs=WOOCOMMERCE_TARGETS,
            max_pages=max(0, args.woocommerce_pages),
        ),
    ]

    original_argv = sys.argv[:]
    try:
        sys.argv = ["normalise_eu_retailer_inventory.py"]
        normalise_main()
    finally:
        sys.argv = original_argv

    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "purpose": "EU retailer discovery orchestration only. No SQL writes.",
        "normalisedOutputFile": "scrapers/retailers/europe/output/eu_normalised_inventory.json",
        "platforms": platform_reports,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("EU retailer discovery orchestration complete")
    for platform in platform_reports:
        print(
            f"{platform['platform']}: "
            f"{platform['productsAccepted']} accepted, "
            f"{platform['productsRejected']} rejected"
        )
    print(f"Report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
