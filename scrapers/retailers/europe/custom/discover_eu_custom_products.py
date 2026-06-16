from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.europe.common.discovery_utils import (  # noqa: E402
    decorate_rows,
    product_rows_from_json_ld,
    product_rows_from_links,
)
from scrapers.retailers.europe.common.fetch_utils import fetch_text  # noqa: E402


INPUT_FILE = Path("scrapers/retailers/europe/custom/eu_custom_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/europe/custom/output/eu_custom_product_discovery.json")


def discover_target(target: dict, max_pages: int, confirm_blocked: bool = False) -> dict:
    products = []
    rejected = 0
    fetches = []

    urls = target.get("categoryUrls", [])
    if confirm_blocked:
        urls = urls[:1]

    for source_url in urls:
        response = fetch_text(source_url, retries=0)
        fetches.append({
            "url": source_url,
            "status": response.status,
            "httpStatus": response.http_status,
            "finalUrl": response.final_url,
            "reason": response.reason,
        })

        if confirm_blocked or not response.ok:
            continue

        rows = product_rows_from_json_ld(response.text, source_url)
        if not rows:
            rows.extend(product_rows_from_links(response.text, source_url, ["/en/surfboards/", "/en/"]))
        accepted, rejected_count = decorate_rows(rows, target, source_url)
        products.extend(accepted)
        rejected += rejected_count

        if max_pages <= 1:
            continue

    return {
        "target": target["retailerSlug"],
        "productsAccepted": len(products),
        "productsRejected": rejected,
        "fetches": fetches,
        "products": products,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover EU custom/structured surfboard products without SQL writes.")
    parser.add_argument("--run-enabled", action="store_true", help="Fetch enabled targets. Without this, no network calls run.")
    parser.add_argument("--confirm-blocked", action="store_true", help="Fetch one URL for a disabled target only to confirm blocking status.")
    parser.add_argument("--target", default="", help="Optional retailerSlug filter.")
    parser.add_argument("--max-pages", type=int, default=1, help="Reserved for future pagination; currently category URL limited.")
    args = parser.parse_args()

    targets = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    if args.confirm_blocked:
        selected = targets
    else:
        selected = [target for target in targets if args.run_enabled and target.get("enabled") is True]
    if args.target:
        selected = [target for target in selected if target.get("retailerSlug") == args.target]

    results = [discover_target(target, max(1, args.max_pages), args.confirm_blocked) for target in selected]
    products = [product for result in results for product in result["products"]]
    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "confirm_blocked" if args.confirm_blocked else "run_enabled" if args.run_enabled else "dry_run",
        "purpose": "EU custom/structured product discovery only. No SQL import or production table writes.",
        "targetsConfigured": len(targets),
        "targetsSelected": len(selected),
        "results": [{key: value for key, value in result.items() if key != "products"} for result in results],
        "products": products,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"EU custom/structured discovery: {report['mode']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
