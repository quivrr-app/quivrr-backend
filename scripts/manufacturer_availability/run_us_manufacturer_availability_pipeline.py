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
from utils.structured_logging import emit_event, update_job_state  # noqa: E402


REGION_CODE = "US"
SOURCE = "manufacturer_direct"
REPORT_OUTPUT = Path("scripts/manufacturer_availability/output/us_mfa_rollout_plan.json")
BUILD_DIAGNOSTICS_OUTPUT = Path(
    "scrapers/manufacturers/availability/us/output/us_mfa_shopify_diagnostics.json"
)
CONFIRM_TOKEN = "APPLY_US_MFA"
BUILD_COMMAND_TIMEOUT_SECONDS = int(os.getenv("QUIVRR_US_MFA_BUILD_TIMEOUT_SECONDS", "180"))
IMPORT_COMMAND_TIMEOUT_SECONDS = int(os.getenv("QUIVRR_US_MFA_IMPORT_TIMEOUT_SECONDS", "300"))
COMMAND_HEARTBEAT_SECONDS = int(os.getenv("QUIVRR_US_MFA_HEARTBEAT_SECONDS", "30"))
RUNNER_TIMEOUT_SECONDS = int(os.getenv("QUIVRR_US_MFA_RUNNER_TIMEOUT_SECONDS", "360"))
IMPORT_TIME_RESERVE_SECONDS = int(os.getenv("QUIVRR_US_MFA_IMPORT_RESERVE_SECONDS", "120"))
IMPLEMENTED_BRANDS = {
    "js_industries": {
        "brandName": "JS Industries",
        "sourceUrl": "https://us.jsindustries.com",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "channel_islands": {
        "brandName": "Channel Islands",
        "sourceUrl": "https://cisurfboards.com",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "pyzel": {
        "brandName": "Pyzel",
        "sourceUrl": "https://pyzelsurfboards.com",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "firewire": {
        "brandName": "Firewire",
        "sourceUrl": "https://firewiresurfboards.com",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "album": {
        "brandName": "Album",
        "sourceUrl": "https://albumsurf.com",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "haydenshapes": {
        "brandName": "Haydenshapes",
        "sourceUrl": "https://haydenshapes.com",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "dhd": {
        "brandName": "DHD",
        "sourceUrl": "https://dhdsurf.com",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "rusty": {
        "brandName": "Rusty",
        "sourceUrl": "https://rustysurfboards.com",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "sharpeye": {
        "brandName": "Sharp Eye",
        "sourceUrl": "https://sharpeyesurfboards.com",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "christenson": {
        "brandName": "Christenson",
        "sourceUrl": "https://christensonsurfboards.com/surfboard-stock",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "misfit": {
        "brandName": "Misfit Shapes",
        "sourceUrl": "https://misfitshapes.com/collections/current-models",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "chilli": {
        "brandName": "Chilli",
        "sourceUrl": "https://www.chillisurfboards.com/?region=usa&direct=1",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
    "pukas": {
        "brandName": "Pukas",
        "sourceUrl": "https://pukassurfshop.com/collections/pukas-surfboards",
        "builder": "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
        "validated": True,
    },
}
SKIPPED_BRANDS = {
    "Lost": "Direct Manufacturer Stock Not Available. The US site exposes board catalogue pages plus dealer and online-dealer referrals rather than purchasable manufacturer-direct inventory items.",
    "Chemistry": "Official products feed returned 403 during lightweight validation.",
    "Simon Anderson": "Australia-only manufacturer-direct source. Do not add to USA MFA.",
}


class CommandTimeoutError(RuntimeError):
    """Raised when a child process exceeds the runner timeout budget."""


def assert_region_scope() -> None:
    configured = os.getenv("QUIVRR_REGION_CODE", REGION_CODE).strip().upper()
    if configured != REGION_CODE:
        raise RuntimeError(
            f"US MFA pipeline refused QUIVRR_REGION_CODE={configured!r}; expected 'US'."
        )


def run(
    command: list[str],
    *,
    attempts: int = 1,
    timeout_seconds: int | None = None,
    progress_label: str = "",
) -> None:
    for attempt in range(1, attempts + 1):
        label = progress_label or command[-1]
        print(
            f"Command attempt {attempt}/{attempts} [{label}]: {' '.join(command)}",
            flush=True,
        )
        started = time.perf_counter()
        process = subprocess.Popen(command, cwd=ROOT)
        last_heartbeat = started
        while True:
            return_code = process.poll()
            now = time.perf_counter()
            if return_code is not None:
                if return_code == 0:
                    print(
                        f"Command completed [{label}] in {round(now - started, 3)}s",
                        flush=True,
                    )
                    return
                break
            if timeout_seconds and (now - started) >= timeout_seconds:
                process.kill()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
                raise CommandTimeoutError(
                    f"US MFA command timed out after {timeout_seconds}s [{label}]"
                )
            if COMMAND_HEARTBEAT_SECONDS > 0 and (now - last_heartbeat) >= COMMAND_HEARTBEAT_SECONDS:
                print(
                    f"Command still running [{label}] after {round(now - started, 1)}s",
                    flush=True,
                )
                last_heartbeat = now
            time.sleep(1)
        completed = process
        if completed.returncode == 0:
            return
        if attempt < attempts:
            time.sleep(5)
    raise RuntimeError(
        f"US MFA command failed with exit code {completed.returncode}: {' '.join(command)}"
    )


def region_counts() -> dict[str, int]:
    last_error = None
    for attempt in range(1, 6):
        engine = build_engine()
        try:
            with connect_with_retry(engine) as conn:
                result = {
                    (row.RegionCode or "<NULL>"): int(row.InventoryRows)
                    for row in conn.execute(
                        text(
                            """
                            SELECT RegionCode, COUNT(*) AS InventoryRows
                            FROM dbo.ManufacturerInventory
                            GROUP BY RegionCode
                            """
                        )
                    )
                }
            return {key: result.get(key, 0) for key in ("AU", "EU", "ID", "US", "<NULL>")}
        except SQLAlchemyError as error:
            last_error = error
            if attempt == 5:
                raise
            print(f"SQL count attempt {attempt}/5 failed; retrying in 10 seconds", flush=True)
            time.sleep(10)
        finally:
            engine.dispose()
    raise last_error


def output_path_for_slug(slug: str) -> Path:
    return Path(
        f"scrapers/manufacturers/availability/{slug}/output/{slug}_us_manufacturer_inventory.json"
    )


def validate_output(slug: str) -> dict:
    path = output_path_for_slug(slug)
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not rows:
        raise RuntimeError(f"US MFA output is empty: {path}")
    for index, row in enumerate(rows):
        if row.get("regionCode") != REGION_CODE:
            raise RuntimeError(f"Unsafe RegionCode in {path} row {index}")
        if row.get("availabilitySource") != SOURCE:
            raise RuntimeError(f"Unsafe AvailabilitySource in {path} row {index}")
        if row.get("priceAmount") is not None and not str(row.get("priceCurrency") or "").strip():
            raise RuntimeError(f"Missing priceCurrency in {path} row {index}")
    return {
        "brand": IMPLEMENTED_BRANDS[slug]["brandName"],
        "rows": len(rows),
        "available_rows": sum(1 for row in rows if row.get("isAvailable")),
        "rows_with_dimensions": sum(1 for row in rows if row.get("lengthFeetInches")),
        "output": str(path),
    }


def load_builder_diagnostic(slug: str) -> dict:
    last_error = None
    for _attempt in range(1, 6):
        try:
            payload = json.loads(BUILD_DIAGNOSTICS_OUTPUT.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.5)
            continue
        for item in payload:
            if item.get("slug") == slug:
                return item
        last_error = RuntimeError(f"US MFA builder diagnostics missing slug {slug}")
        time.sleep(0.5)
    raise last_error


def degrade_brand_diagnostic(
    slug: str,
    *,
    source_status: str,
    error_type: str,
    error_message_summary: str,
) -> dict:
    return {
        "slug": slug,
        "brand": IMPLEMENTED_BRANDS[slug]["brandName"],
        "source_url": IMPLEMENTED_BRANDS[slug]["sourceUrl"],
        "source_status": source_status,
        "fresh_build_success": False,
        "used_stale_fallback": False,
        "rows_emitted": 0,
        "error_type": error_type,
        "error_message_summary": error_message_summary,
    }


def timeout_budget_for_build(started_at: float) -> int:
    elapsed = time.perf_counter() - started_at
    remaining = max(0, RUNNER_TIMEOUT_SECONDS - elapsed)
    budget = remaining - IMPORT_TIME_RESERVE_SECONDS
    return max(0, min(BUILD_COMMAND_TIMEOUT_SECONDS, int(budget)))


def build_brand(slug: str, *, position: int, total: int, timeout_seconds: int | None = None) -> dict:
    target = IMPLEMENTED_BRANDS[slug]
    started = time.perf_counter()
    print(
        f"Starting US MFA brand {position}/{total}: {target['brandName']}",
        flush=True,
    )
    emit_event(
        "mfa_brand_started",
        "manufacturer_availability",
        region=REGION_CODE,
        status="success",
        brand=target["brandName"],
    )
    try:
        run(
            [
                sys.executable,
                "scrapers/manufacturers/availability/us/build_us_shopify_availability.py",
                "--brand",
                slug,
            ],
            timeout_seconds=timeout_seconds or BUILD_COMMAND_TIMEOUT_SECONDS,
            progress_label=f"build:{target['brandName']}",
        )
    except CommandTimeoutError as exc:
        diagnostic = degrade_brand_diagnostic(
            slug,
            source_status="command_timeout",
            error_type=type(exc).__name__,
            error_message_summary=str(exc),
        )
        emit_event(
            "mfa_brand_degraded",
            "manufacturer_availability",
            region=REGION_CODE,
            status="warning",
            brand=target["brandName"],
            source_status=diagnostic["source_status"],
            used_stale_fallback=False,
            error_type=diagnostic["error_type"],
            error_message=diagnostic["error_message_summary"],
            rows=0,
        )
        print(
            f"Completed US MFA brand {position}/{total}: {target['brandName']} degraded in "
            f"{round(time.perf_counter() - started, 3)}s",
            flush=True,
        )
        return diagnostic
    except RuntimeError as exc:
        diagnostic = degrade_brand_diagnostic(
            slug,
            source_status="command_failed",
            error_type=type(exc).__name__,
            error_message_summary=str(exc),
        )
        emit_event(
            "mfa_brand_degraded",
            "manufacturer_availability",
            region=REGION_CODE,
            status="warning",
            brand=target["brandName"],
            source_status=diagnostic["source_status"],
            used_stale_fallback=False,
            error_type=diagnostic["error_type"],
            error_message=diagnostic["error_message_summary"],
            rows=0,
        )
        print(
            f"Completed US MFA brand {position}/{total}: {target['brandName']} degraded in "
            f"{round(time.perf_counter() - started, 3)}s",
            flush=True,
        )
        return diagnostic
    diagnostic = load_builder_diagnostic(slug)
    if diagnostic.get("used_stale_fallback"):
        emit_event(
            "mfa_brand_degraded",
            "manufacturer_availability",
            region=REGION_CODE,
            status="warning",
            brand=target["brandName"],
            source_status=diagnostic.get("source_status"),
            used_stale_fallback=True,
            error_type=diagnostic.get("error_type"),
            error_message=diagnostic.get("error_message_summary"),
            rows=diagnostic.get("rows_emitted"),
        )
    elif not diagnostic.get("fresh_build_success"):
        emit_event(
            "mfa_brand_degraded",
            "manufacturer_availability",
            region=REGION_CODE,
            status="warning",
            brand=target["brandName"],
            source_status=diagnostic.get("source_status"),
            used_stale_fallback=False,
            error_type=diagnostic.get("error_type"),
            error_message=diagnostic.get("error_message_summary"),
            rows=diagnostic.get("rows_emitted"),
        )
    else:
        emit_event(
            "mfa_brand_completed",
            "manufacturer_availability",
            region=REGION_CODE,
            status="success",
            brand=target["brandName"],
            rows=diagnostic.get("rows_emitted"),
        )
    print(
        f"Completed US MFA brand {position}/{total}: {target['brandName']} in "
        f"{round(time.perf_counter() - started, 3)}s",
        flush=True,
    )
    return diagnostic


def import_report() -> dict:
    path = Path("scripts/manufacturer_availability/output/us_mfa_import_report.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def build_rollout_report(
    build_diagnostics: dict[str, dict],
    validated_outputs: dict[str, dict],
    import_payload: dict | None = None,
) -> dict:
    diagnostics_by_brand = {
        item["brand"]: item for item in (import_payload or {}).get("brands", [])
    }
    brands = []
    for slug, target in IMPLEMENTED_BRANDS.items():
        build_result = build_diagnostics.get(slug, {})
        validated = validated_outputs.get(slug, {})
        linked = diagnostics_by_brand.get(target["brandName"], {})
        brands.append(
            {
                "brandName": target["brandName"],
                "sourceUrl": target["sourceUrl"],
                "builder": target["builder"],
                "enabled": True,
                "validated": target["validated"],
                "status": "implemented"
                if build_result.get("fresh_build_success")
                else build_result.get("source_status") or "failed",
                "source_status": build_result.get("source_status"),
                "fresh_build_success": build_result.get("fresh_build_success"),
                "used_stale_fallback": build_result.get("used_stale_fallback"),
                "rows_emitted": build_result.get("rows_emitted"),
                "error_type": build_result.get("error_type"),
                "error_message_summary": build_result.get("error_message_summary"),
                "discovered_products": validated.get("rows"),
                "normalised_rows": validated.get("rows"),
                "available_rows": validated.get("available_rows"),
                "linked_model_rows": linked.get("linked_model_rows"),
                "linked_size_rows": linked.get("linked_size_rows"),
                "skipped_reason": None,
            }
        )
    for brand_name, reason in sorted(SKIPPED_BRANDS.items()):
        brands.append(
            {
                "brandName": brand_name,
                "sourceUrl": None,
                "builder": None,
                "enabled": False,
                "validated": False,
                "status": "skipped",
                "source_status": "skipped",
                "fresh_build_success": False,
                "used_stale_fallback": False,
                "rows_emitted": 0,
                "error_type": None,
                "error_message_summary": None,
                "discovered_products": None,
                "normalised_rows": None,
                "available_rows": None,
                "linked_model_rows": None,
                "linked_size_rows": None,
                "skipped_reason": reason,
            }
        )
    return {
        "regionCode": REGION_CODE,
        "brandsAttempted": len(IMPLEMENTED_BRANDS),
        "implementedBrandCount": len(IMPLEMENTED_BRANDS),
        "freshBrandCount": sum(
            1 for item in build_diagnostics.values() if item.get("fresh_build_success")
        ),
        "degradedBrandCount": sum(
            1 for item in build_diagnostics.values() if not item.get("fresh_build_success")
        ),
        "minimumAcceptableOutcomeMet": (
            sum(1 for item in build_diagnostics.values() if item.get("fresh_build_success")) >= 2
        ),
        "brands": brands,
        "importReport": import_payload or {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validated US manufacturer availability pipeline."
    )
    parser.add_argument("execution_mode", nargs="?", choices=["apply", "dry-run"])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply US-only manufacturer inventory.")
    mode.add_argument("--dry-run", action="store_true", help="Build and validate without SQL writes.")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--confirm-apply-us-mfa", default="")
    args = parser.parse_args()
    if args.execution_mode == "apply":
        args.apply = True
    elif args.execution_mode == "dry-run":
        args.dry_run = True

    assert_region_scope()
    if args.apply and args.confirm_apply_us_mfa != CONFIRM_TOKEN:
        raise RuntimeError(
            f"US MFA apply mode requires explicit confirmation via --confirm-apply-us-mfa {CONFIRM_TOKEN}."
        )

    started = time.perf_counter()
    emit_event("mfa_refresh_started", "manufacturer_availability", region=REGION_CODE, status="success")
    before = region_counts()
    print("ManufacturerInventory before:", json.dumps(before, sort_keys=True), flush=True)
    if before["<NULL>"]:
        raise RuntimeError("US MFA pipeline refused: NULL RegionCode rows already exist.")

    build_diagnostics: dict[str, dict] = {}
    if not args.skip_build:
        total_brands = len(IMPLEMENTED_BRANDS)
        for position, slug in enumerate(IMPLEMENTED_BRANDS, start=1):
            build_timeout = timeout_budget_for_build(started)
            if build_timeout <= 0:
                build_diagnostics[slug] = degrade_brand_diagnostic(
                    slug,
                    source_status="runner_timeout_budget_exhausted",
                    error_type="CommandTimeoutError",
                    error_message_summary=(
                        "US MFA runner exhausted its build-time budget before this brand started."
                    ),
                )
                emit_event(
                    "mfa_brand_degraded",
                    "manufacturer_availability",
                    region=REGION_CODE,
                    status="warning",
                    brand=IMPLEMENTED_BRANDS[slug]["brandName"],
                    source_status=build_diagnostics[slug]["source_status"],
                    used_stale_fallback=False,
                    error_type=build_diagnostics[slug]["error_type"],
                    error_message=build_diagnostics[slug]["error_message_summary"],
                    rows=0,
                )
                print(
                    f"Skipping US MFA brand {position}/{total_brands}: "
                    f"{IMPLEMENTED_BRANDS[slug]['brandName']} due to runner timeout budget",
                    flush=True,
                )
                continue
            build_diagnostics[slug] = build_brand(
                slug,
                position=position,
                total=total_brands,
                timeout_seconds=build_timeout,
            )
    else:
        for slug in IMPLEMENTED_BRANDS:
            validated = validate_output(slug)
            build_diagnostics[slug] = {
                "slug": slug,
                "brand": IMPLEMENTED_BRANDS[slug]["brandName"],
                "source_status": "fresh",
                "fresh_build_success": True,
                "used_stale_fallback": False,
                "rows_emitted": validated["rows"],
                "error_type": None,
                "error_message_summary": None,
            }

    validated_outputs = {}
    for slug, diagnostic in build_diagnostics.items():
        if diagnostic.get("fresh_build_success") or diagnostic.get("used_stale_fallback"):
            validated_outputs[slug] = validate_output(slug)
    print("Validated US MFA outputs:", json.dumps(validated_outputs, sort_keys=True), flush=True)

    successful_fresh_brands = [
        IMPLEMENTED_BRANDS[slug]["brandName"]
        for slug, diagnostic in build_diagnostics.items()
        if diagnostic.get("fresh_build_success")
    ]
    if not successful_fresh_brands:
        raise RuntimeError("US MFA pipeline produced no fresh brand outputs.")

    import_command = [
        sys.executable,
        "scripts/manufacturer_availability/import_us_manufacturer_availability.py",
        "--brands",
        ",".join(successful_fresh_brands),
    ]
    if args.apply:
        import_command.extend(["--apply", "--confirm-apply-us-mfa", CONFIRM_TOKEN])
    print(
        f"Starting US MFA importer for {len(successful_fresh_brands)} fresh brands",
        flush=True,
    )
    elapsed_before_import = time.perf_counter() - started
    remaining_import_budget = max(30, int(RUNNER_TIMEOUT_SECONDS - elapsed_before_import))
    run(
        import_command,
        attempts=3,
        timeout_seconds=min(IMPORT_COMMAND_TIMEOUT_SECONDS, remaining_import_budget),
        progress_label="import:US manufacturer availability",
    )
    print("Completed US MFA importer", flush=True)
    import_payload = import_report()
    report = build_rollout_report(build_diagnostics, validated_outputs, import_payload)
    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    after = region_counts()
    print("ManufacturerInventory after:", json.dumps(after, sort_keys=True), flush=True)
    if after["AU"] != before["AU"] or after["EU"] != before["EU"] or after["ID"] != before["ID"]:
        raise RuntimeError("Protected AU, EU, or ID ManufacturerInventory count changed.")
    if after["<NULL>"] != 0:
        raise RuntimeError("US MFA pipeline created NULL RegionCode rows.")
    if args.apply and after["US"] <= 0:
        raise RuntimeError("US MFA pipeline produced no US ManufacturerInventory rows.")

    total_rows = sum(item["rows"] for item in validated_outputs.values())
    import_brands = (import_payload or {}).get("brands", [])
    emit_event(
        "mfa_refresh_completed",
        "manufacturer_availability",
        region=REGION_CODE,
        status="success",
        total_brands_attempted=len(IMPLEMENTED_BRANDS),
        successful_brands=len(successful_fresh_brands),
        degraded_brands=sum(
            1
            for item in build_diagnostics.values()
            if not item.get("fresh_build_success")
        ),
        rows_imported=total_rows,
        available_rows=sum(item.get("available_rows", 0) for item in validated_outputs.values()),
        linked_model_rows=sum(item.get("linked_model_rows", 0) or 0 for item in import_brands),
        linked_size_rows=sum(item.get("linked_size_rows", 0) or 0 for item in import_brands),
        duration_seconds=round(time.perf_counter() - started, 3),
    )
    update_job_state(
        "mfa_us",
        "mfa",
        "manufacturer_availability",
        "success",
        region=REGION_CODE,
        rows=total_rows,
        duration_seconds=round(time.perf_counter() - started, 3),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit_event(
            "mfa_refresh_failed",
            "manufacturer_availability",
            region=REGION_CODE,
            status="failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        update_job_state(
            "mfa_us",
            "mfa",
            "manufacturer_availability",
            "failed",
            region=REGION_CODE,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise
