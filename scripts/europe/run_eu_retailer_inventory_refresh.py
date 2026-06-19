from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
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


REGION_CODE = "EU"
DEFAULT_INPUT = Path("scrapers/retailers/europe/output/eu_normalised_inventory.json")
PRESTASHOP_REPORT = Path(
    "scrapers/retailers/europe/prestashop/output/eu_prestashop_product_discovery.json"
)
MINIMUM_ROWS = {
    "58_surf": 1200,
    "pukas_surf_shop": 1800,
    "bell_surf": 350,
    "surf_boss": 300,
    "surf_corner": 100,
    "mundo_surf": 3800,
    "single_quiver": 300,
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
    failures = {
        result.get("target", "<missing>"): int(result.get("detailFetchFailures") or 0)
        for result in report.get("results", [])
        if int(result.get("detailFetchFailures") or 0) > 0
    }
    if failures:
        raise RuntimeError(f"EU detail-page discovery failures must be zero: {failures}")


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

    after = region_counts()
    print("RetailerInventory after:", json.dumps(after, sort_keys=True), flush=True)
    if after["AU"] != before["AU"] or after["ID"] != before["ID"]:
        raise RuntimeError("Protected AU or ID RetailerInventory count changed.")
    if after["<NULL>"] != 0:
        raise RuntimeError("EU refresh created NULL RegionCode rows.")
    if args.apply and after["EU"] < before["EU"]:
        raise RuntimeError("EU RetailerInventory count unexpectedly decreased.")


if __name__ == "__main__":
    main()
