from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
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
SOURCE = "manufacturer_direct"
APPROVED_BRANDS = {
    "js_industries": "JS Industries",
    "pyzel": "Pyzel",
    "firewire": "Firewire",
    "haydenshapes": "Haydenshapes",
    "rusty": "Rusty",
    "sharp_eye": "Sharp Eye",
    "dhd": "DHD",
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
        f"EU MFA command failed with exit code {completed.returncode}: {' '.join(command)}"
    )


def assert_region_scope() -> None:
    configured = os.getenv("QUIVRR_REGION_CODE", REGION_CODE).strip().upper()
    if configured != REGION_CODE:
        raise RuntimeError(
            f"EU MFA pipeline refused QUIVRR_REGION_CODE={configured!r}; expected 'EU'."
        )


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
                        FROM dbo.ManufacturerInventory
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


def validate_output(slug: str) -> int:
    path = Path(
        f"scrapers/manufacturers/availability/{slug}/output/"
        f"{slug}_eu_manufacturer_inventory.json"
    )
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not rows:
        raise RuntimeError(f"EU MFA output is empty: {path}")
    for index, row in enumerate(rows):
        if row.get("regionCode") != REGION_CODE:
            raise RuntimeError(f"Unsafe RegionCode in {path} row {index}")
        if row.get("availabilitySource") != SOURCE:
            raise RuntimeError(f"Unsafe AvailabilitySource in {path} row {index}")
        if row.get("priceAmount") is not None and row.get("priceCurrency") != "EUR":
            raise RuntimeError(f"Unsafe priced currency in {path} row {index}")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validated EU manufacturer availability pipeline.")
    parser.add_argument("execution_mode", nargs="?", choices=["apply", "dry-run"])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply EU-only manufacturer inventory.")
    mode.add_argument("--dry-run", action="store_true", help="Build and validate without SQL writes.")
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Validate and import existing EU MFA outputs without fetching sources.",
    )
    args = parser.parse_args()
    if args.execution_mode == "apply":
        args.apply = True
    elif args.execution_mode == "dry-run":
        args.dry_run = True

    assert_region_scope()
    before = region_counts()
    print("ManufacturerInventory before:", json.dumps(before, sort_keys=True), flush=True)
    if before["<NULL>"]:
        raise RuntimeError("EU MFA pipeline refused: NULL RegionCode rows already exist.")

    if not args.skip_build:
        for slug in APPROVED_BRANDS:
            if slug == "dhd":
                command = [
                    sys.executable,
                    "scrapers/manufacturers/availability/dhd/build_dhd_eu_availability.py",
                ]
            else:
                command = [
                    sys.executable,
                    "scrapers/manufacturers/availability/eu/build_eu_shopify_availability.py",
                    "--brand",
                    slug,
                ]
            run(command)

    output_counts = {slug: validate_output(slug) for slug in APPROVED_BRANDS}
    print("Validated EU MFA outputs:", json.dumps(output_counts, sort_keys=True), flush=True)

    command = [
        sys.executable,
        "scripts/manufacturer_availability/import_eu_manufacturer_availability.py",
        "--brands",
        ",".join(APPROVED_BRANDS.values()),
    ]
    if args.apply:
        command.append("--apply")
    run(command, attempts=3)

    after = region_counts()
    print("ManufacturerInventory after:", json.dumps(after, sort_keys=True), flush=True)
    if after["AU"] != before["AU"] or after["ID"] != before["ID"]:
        raise RuntimeError("Protected AU or ID ManufacturerInventory count changed.")
    if after["<NULL>"] != 0:
        raise RuntimeError("EU MFA pipeline created NULL RegionCode rows.")
    if args.apply and after["EU"] <= 0:
        raise RuntimeError("EU MFA pipeline produced no EU ManufacturerInventory rows.")


if __name__ == "__main__":
    main()
