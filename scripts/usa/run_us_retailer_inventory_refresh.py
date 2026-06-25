from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.structured_logging import emit_event, update_job_state


REGION_CODE = "US"
DEFAULT_INPUT = Path("scrapers/retailers/usa/output/us_normalised_inventory.json")
MINIMUM_ROWS = {
    "surf_station": 100,
    "jacks_surfboards": 50,
    "real_watersports": 50,
    "cleanline_surf": 50,
    "hawaiian_south_shore": 50,
    "birds_surf_shed": 10,
    "island_water_sports": 1,
    "surf_n_sea": 1,
    "kimos_surf_hut": 1,
    "moment_surf_co": 1,
    "degree_33_surfboards": 1,
    "surfboard_broker": 1,
    "infinity_surfboards": 1,
    "walden_surfboards": 1,
    "stewart_surfboards": 1,
    "bing_surfboards": 1,
    "robert_august_surf_company": 1,
    "dark_arts_surf": 1,
    "catalyst_surf_shop": 1,
    "warm_winds": 1,
}


def assert_region_scope() -> None:
    configured = os.getenv("QUIVRR_REGION_CODE", REGION_CODE).strip().upper()
    if configured != REGION_CODE:
        raise RuntimeError(
            f"US retailer refresh refused QUIVRR_REGION_CODE={configured!r}; expected 'US'."
        )


def load_and_validate_rows(path: Path) -> tuple[list[dict], dict[str, int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("rows", [])
    if not isinstance(rows, list):
        raise RuntimeError(f"US normalised input has no rows list: {path}")
    invalid = [index for index, row in enumerate(rows) if row.get("regionCode") != REGION_CODE]
    if invalid:
        raise RuntimeError(
            f"US retailer refresh found {len(invalid)} non-US rows; first index={invalid[0]}."
        )
    counts: dict[str, int] = {}
    for row in rows:
        slug = row.get("retailerSlug") or ""
        counts[slug] = counts.get(slug, 0) + 1
    shallow = {
        retailer: {"actual": counts.get(retailer, 0), "minimum": minimum}
        for retailer, minimum in MINIMUM_ROWS.items()
        if counts.get(retailer, 0) < minimum
    }
    if shallow:
        raise RuntimeError(f"US discovery coverage below safe minimums: {shallow}")
    return rows, counts


def build_summary(rows: list[dict]) -> dict:
    by_retailer = Counter(row.get("retailerSlug") or "" for row in rows)
    importable = [row for row in rows if row.get("importableRaw")]
    dimensions = [
        row
        for row in rows
        if row.get("lengthFeetInches") or row.get("volumeLitres") is not None
    ]
    price_rows = [row for row in rows if row.get("priceAmount") is not None]
    image_rows = [row for row in rows if row.get("productImageUrl")]
    return {
        "regionCode": REGION_CODE,
        "retailerCount": len(by_retailer),
        "totalNormalisedRows": len(rows),
        "importableRows": len(importable),
        "rejectedRows": len(rows) - len(importable),
        "rowsWithDimensions": len(dimensions),
        "rowsWithPrice": len(price_rows),
        "rowsWithImage": len(image_rows),
        "rowsByRetailer": dict(sorted(by_retailer.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="US-only retailer discovery, validation, and guarded SQL refresh."
    )
    parser.add_argument("execution_mode", nargs="?", choices=["apply", "dry-run"])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply guarded US-only SQL upserts.")
    mode.add_argument("--dry-run", action="store_true", help="Validate without SQL writes.")
    parser.add_argument("--skip-discovery", action="store_true", help="Use an existing normalised input instead of fetching retailer sources.")
    parser.add_argument("--input", type=Path)
    parser.add_argument(
        "--confirm-apply-us",
        default="",
        help="Required confirmation token for live US apply.",
    )
    args = parser.parse_args()
    if args.execution_mode == "apply":
        args.apply = True
    elif args.execution_mode == "dry-run":
        args.dry_run = True
    input_path = args.input or DEFAULT_INPUT

    assert_region_scope()
    if args.apply and args.confirm_apply_us != "APPLY_US":
        raise RuntimeError(
            "US apply mode requires explicit confirmation via --confirm-apply-us APPLY_US."
        )
    emit_event("inventory_refresh_started", "retailer_inventory", region=REGION_CODE, status="success")

    if not args.skip_discovery:
        command = [sys.executable, "scrapers/retailers/usa/run_us_retailer_discovery.py", "--dry-run"]
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode != 0:
            raise RuntimeError(f"US retailer discovery dry-run failed with exit code {completed.returncode}")

    if not input_path.exists():
        print("Dry run complete: US target metadata passed; no existing normalised input to inspect.")
        update_job_state("inventory_us", "inventory", "retailer_inventory", "success", region=REGION_CODE, rows_loaded=0)
        return

    rows, retailer_counts = load_and_validate_rows(input_path)
    summary = build_summary(rows)
    print("Validated US normalised rows:", len(rows))
    print("Rows by retailer:", json.dumps(retailer_counts, sort_keys=True))
    print("US retailer readiness summary:", json.dumps(summary, sort_keys=True))

    if args.apply:
        importer_command = [
            sys.executable,
            "scripts/usa/import_us_retailer_inventory.py",
            "--input",
            str(input_path),
            "--apply",
            "--confirm-apply-us",
            args.confirm_apply_us,
        ]
        completed = subprocess.run(importer_command, cwd=ROOT)
        if completed.returncode != 0:
            raise RuntimeError(
                f"US retailer inventory apply failed with exit code {completed.returncode}"
            )

    emit_event(
        "inventory_refresh_completed",
        "retailer_inventory",
        region=REGION_CODE,
        status="success",
        rows_loaded=len(rows),
        retailer_count=summary["retailerCount"],
        importable_rows=summary["importableRows"],
    )
    update_job_state(
        "inventory_us",
        "inventory",
        "retailer_inventory",
        "success",
        region=REGION_CODE,
        rows_loaded=len(rows),
        retailer_count=summary["retailerCount"],
        importable_rows=summary["importableRows"],
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit_event(
            "inventory_refresh_failed",
            "retailer_inventory",
            region=REGION_CODE,
            status="failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        update_job_state(
            "inventory_us",
            "inventory",
            "retailer_inventory",
            "failed",
            region=REGION_CODE,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise
