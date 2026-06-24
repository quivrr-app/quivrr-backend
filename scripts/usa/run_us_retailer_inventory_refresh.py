from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
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
    "hansen_surfboards": 50,
    "hawaiian_south_shore": 50,
    "encinitas_surfboards": 10,
    "birds_surf_shed": 10,
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="US-only retailer discovery and validation scaffold. No SQL writes in Phase 1."
    )
    parser.add_argument("execution_mode", nargs="?", choices=["apply", "dry-run"])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Reserved for future US SQL upserts.")
    mode.add_argument("--dry-run", action="store_true", help="Validate without SQL writes.")
    parser.add_argument("--skip-discovery", action="store_true", help="Use an existing normalised input instead of fetching retailer sources.")
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    if args.execution_mode == "apply":
        args.apply = True
    elif args.execution_mode == "dry-run":
        args.dry_run = True
    input_path = args.input or DEFAULT_INPUT

    assert_region_scope()
    emit_event("inventory_refresh_started", "retailer_inventory", region=REGION_CODE, status="success")

    if args.apply:
        raise RuntimeError(
            "US retailer refresh apply mode is intentionally disabled in Phase 1. "
            "This scaffold may build discovery output only and must not write SQL yet."
        )

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
    print("Validated US normalised rows:", len(rows))
    print("Rows by retailer:", json.dumps(retailer_counts, sort_keys=True))
    emit_event(
        "inventory_refresh_completed",
        "retailer_inventory",
        region=REGION_CODE,
        status="success",
        rows_loaded=len(rows),
    )
    update_job_state(
        "inventory_us",
        "inventory",
        "retailer_inventory",
        "success",
        region=REGION_CODE,
        rows_loaded=len(rows),
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
