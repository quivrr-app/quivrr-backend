from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
import math
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.europe.import_eu_retailer_inventory import (  # noqa: E402
    build_engine,
    connect_with_retry,
)
from utils.structured_logging import emit_event, update_job_state


REGION_CODE = "EU"
DEFAULT_INPUT = Path("scrapers/retailers/europe/output/eu_normalised_inventory.json")
PRESTASHOP_REPORT = Path(
    "scrapers/retailers/europe/prestashop/output/eu_prestashop_product_discovery.json"
)
DETAIL_FETCH_FAILURE_ABSOLUTE_LIMIT = 20
DETAIL_FETCH_FAILURE_RATE_LIMIT = 0.01
MINIMUM_ROWS = {
    "58_surf": 300,
    "pukas_surf_shop": 1800,
    "bell_surf": 350,
    "board_exchange": 100,
    "pop_up_surf_shop": 70,
    "noordzee_boardstore": 100,
    "gsi_europe": 10,
    "surf_boss": 300,
    "surf_corner": 100,
    "tablas_surf_shop": 80,
    "mundo_surf": 3800,
    "single_quiver": 300,
    "hart_beach": 80,
    "hawaiisurf": 30,
    "santoloco": 100,
    "surf_pirates": 40,
}


def run(command: list[str], attempts: int = 1) -> None:
    for attempt in range(1, attempts + 1):
        print(f"Command attempt {attempt}/{attempts}:", " ".join(command), flush=True)
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode == 0:
            return
        if attempt < attempts:
            time.sleep(10)
    raise RuntimeError(
        f"EU retailer refresh command failed with exit code {completed.returncode}: "
        f"{' '.join(command)}"
    )


def assert_region_scope() -> None:
    configured = os.getenv("QUIVRR_REGION_CODE", REGION_CODE).strip().upper()
    if configured != REGION_CODE:
        raise RuntimeError(
            f"EU retailer refresh refused QUIVRR_REGION_CODE={configured!r}; expected 'EU'."
        )


def load_and_validate_rows(path: Path) -> tuple[list[dict], Counter]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("rows", [])
    if not isinstance(rows, list):
        raise RuntimeError(f"EU normalised input has no rows list: {path}")
    invalid = [index for index, row in enumerate(rows) if row.get("regionCode") != REGION_CODE]
    if invalid:
        raise RuntimeError(
            f"EU retailer refresh found {len(invalid)} non-EU rows; first index={invalid[0]}."
        )
    counts = Counter(row.get("retailerSlug") for row in rows)
    shallow = {
        retailer: {"actual": counts.get(retailer, 0), "minimum": minimum}
        for retailer, minimum in MINIMUM_ROWS.items()
        if counts.get(retailer, 0) < minimum
    }
    if shallow:
        raise RuntimeError(f"EU discovery coverage below safe minimums: {shallow}")
    return rows, counts


def assert_detail_fetch_health(path: Path = PRESTASHOP_REPORT) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))
    hard_failures: dict[str, dict[str, int]] = {}
    soft_failures: dict[str, dict[str, int]] = {}
    for result in report.get("results", []):
        failures = int(result.get("detailFetchFailures") or 0)
        if failures <= 0:
            continue
        accepted = int(
            result.get("productsAccepted")
            or result.get("uniqueCanonicalProducts")
            or 0
        )
        failure_budget = min(
            DETAIL_FETCH_FAILURE_ABSOLUTE_LIMIT,
            max(1, math.ceil(accepted * DETAIL_FETCH_FAILURE_RATE_LIMIT)) if accepted else 0,
        )
        summary = {
            "failures": failures,
            "accepted": accepted,
            "budget": failure_budget,
        }
        if accepted <= 0 or failures > failure_budget:
            hard_failures[result.get("target", "<missing>")] = summary
        else:
            soft_failures[result.get("target", "<missing>")] = summary

    for retailer, summary in soft_failures.items():
        emit_event(
            "retailer_detail_fetch_degraded",
            "retailer_inventory",
            region=REGION_CODE,
            status="degraded",
            retailer=retailer,
            detail_failures=summary["failures"],
            accepted_products=summary["accepted"],
            allowed_failures=summary["budget"],
        )
        print(
            f"Allowed bounded EU detail-page failures for {retailer}: "
            f"{summary['failures']} of {summary['accepted']} accepted products "
            f"(budget {summary['budget']})",
            flush=True,
        )

    if hard_failures:
        raise RuntimeError(f"EU detail-page discovery failures exceeded budget: {hard_failures}")


def region_counts() -> dict[str, int]:
    last_error = None
    for attempt in range(1, 6):
        engine = build_engine()
        try:
            with connect_with_retry(engine) as conn:
                result = {
                    (row.RegionCode or "<NULL>"): int(row.InventoryRows)
                    for row in conn.execute(text("""
                        SELECT RegionCode, COUNT(*) AS InventoryRows
                        FROM dbo.RetailerInventory
                        GROUP BY RegionCode
                    """))
                }
            return {key: result.get(key, 0) for key in ("AU", "EU", "ID", "<NULL>")}
        except SQLAlchemyError as error:
            last_error = error
            if attempt == 5:
                raise
            print(f"SQL count attempt {attempt}/5 failed; retrying in 10 seconds", flush=True)
            time.sleep(10)
        finally:
            engine.dispose()
    raise last_error


def main() -> None:
    parser = argparse.ArgumentParser(description="EU-only retailer discovery and SQL refresh.")
    parser.add_argument("execution_mode", nargs="?", choices=["apply", "dry-run"])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply EU-only SQL upserts.")
    mode.add_argument("--dry-run", action="store_true", help="Validate without SQL writes.")
    parser.add_argument(
        "--skip-discovery",
        action="store_true",
        help="Use an existing normalised input instead of fetching retailer sources.",
    )
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    if args.execution_mode == "apply":
        args.apply = True
    elif args.execution_mode == "dry-run":
        args.dry_run = True
    input_path = args.input or DEFAULT_INPUT

    assert_region_scope()
    started = time.perf_counter()
    emit_event("inventory_refresh_started", "retailer_inventory", region=REGION_CODE, status="success")
    before = region_counts()
    print("RetailerInventory before:", json.dumps(before, sort_keys=True), flush=True)
    if before["<NULL>"]:
        raise RuntimeError("EU refresh refused: RetailerInventory contains NULL RegionCode rows.")

    if not args.skip_discovery:
        discovery_command = [
            sys.executable,
            "scrapers/retailers/europe/run_eu_retailer_discovery.py",
        ]
        if not args.apply:
            discovery_command.append("--dry-run")
        emit_event("retailer_scrape_started", "retailer_inventory", region=REGION_CODE, status="success", retailer="eu_discovery")
        run(discovery_command)
        if args.apply:
            assert_detail_fetch_health()

    if not input_path.exists():
        if args.apply:
            raise RuntimeError(f"EU normalised input does not exist: {input_path}")
        print("Dry run complete: target metadata passed; no existing normalised input to inspect.")
        return

    if not args.apply and not args.skip_discovery and args.input is None:
        print("Dry run complete: EU target metadata and protected region counts passed.")
        return

    rows, retailer_counts = load_and_validate_rows(input_path)
    print("Validated EU normalised rows:", len(rows), flush=True)
    print("Rows by retailer:", json.dumps(retailer_counts, sort_keys=True), flush=True)
    for retailer, count in sorted(retailer_counts.items()):
        emit_event(
            "retailer_scrape_completed",
            "retailer_inventory",
            region=REGION_CODE,
            status="success",
            retailer=retailer,
            rows_loaded=count,
        )

    with tempfile.TemporaryDirectory(prefix="quivrr-eu-retailer-") as temp_dir:
        command = [
            sys.executable,
            "scripts/europe/import_eu_retailer_inventory.py",
            "--input",
            str(input_path),
            "--output",
            str(Path(temp_dir) / "dry_run.json"),
        ]
        if args.apply:
            command.extend([
                "--apply",
                "--apply-output",
                str(Path(temp_dir) / "apply.json"),
            ])
        run(command, attempts=3)
        if args.apply:
            report_path = Path(temp_dir) / "apply.json"
            if report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                apply_counts = report.get("applyCounts", {})
                emit_event(
                    "inventory_import_completed",
                    "retailer_inventory",
                    region=REGION_CODE,
                    status="success",
                    rows_loaded=len(rows),
                    rows_inserted=apply_counts.get("insertedRows") or apply_counts.get("upsertedRows") or apply_counts.get("inserted"),
                    duration_seconds=round(time.perf_counter() - started, 3),
                )
                linking = report.get("canonicalLinkingAfterApply", {})
                emit_event(
                    "inventory_linking_completed",
                    "retailer_inventory",
                    region=REGION_CODE,
                    status="success",
                    model_links=linking.get("linkedBoardModelIdRows"),
                    size_links=linking.get("linkedBoardSizeIdRows"),
                    duration_seconds=round(time.perf_counter() - started, 3),
                )

    after = region_counts()
    print("RetailerInventory after:", json.dumps(after, sort_keys=True), flush=True)
    if after["AU"] != before["AU"] or after["ID"] != before["ID"]:
        raise RuntimeError("Protected AU or ID RetailerInventory count changed.")
    if after["<NULL>"] != 0:
        raise RuntimeError("EU refresh created NULL RegionCode rows.")
    if args.apply and after["EU"] < before["EU"]:
        raise RuntimeError("EU RetailerInventory count unexpectedly decreased.")
    emit_event(
        "inventory_refresh_completed",
        "retailer_inventory",
        region=REGION_CODE,
        status="success",
        rows_loaded=len(rows),
        duration_seconds=round(time.perf_counter() - started, 3),
    )
    update_job_state(
        "inventory_eu",
        "inventory",
        "retailer_inventory",
        "success",
        region=REGION_CODE,
        rows_loaded=len(rows),
        before_rows=before["EU"],
        after_rows=after["EU"],
        duration_seconds=round(time.perf_counter() - started, 3),
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
            "inventory_eu",
            "inventory",
            "retailer_inventory",
            "failed",
            region=REGION_CODE,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise
