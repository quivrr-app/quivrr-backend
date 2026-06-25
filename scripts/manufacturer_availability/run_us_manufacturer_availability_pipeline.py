from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.structured_logging import emit_event, update_job_state


REGION_CODE = "US"
CONFIG_PATH = Path(
    "scrapers/manufacturers/availability/config/us_manufacturer_availability_targets.example.json"
)
REPORT_OUTPUT = Path("scripts/manufacturer_availability/output/us_mfa_rollout_plan.json")
APPROVED_BRANDS = {
    "Channel Islands": "https://cisurfboards.com",
    "Lost": "https://lostsurfboards.net",
    "Pyzel": "https://pyzelsurfboards.com",
    "JS Industries": "https://us.jsindustries.com",
    "Firewire": "https://firewiresurfboards.com",
    "Album": "https://albumsurf.com",
    "SharpEye": "https://sharpeyesurfboards.com",
    "DHD": "https://dhdsurf.com",
    "Christenson": "https://christensonsurfboards.com",
    "Chemistry": "https://chemistrysurfboards.com",
    "Rusty": "https://rustysurfboards.com",
    "Haydenshapes": "https://haydenshapes.com",
    "Misfit": "https://misfitshapes.com",
    "Chilli": "https://chillisurfboards.com",
    "Pukas": "https://pukasurf.com",
    "Simon Anderson": "https://simonandersonsurfboards.com",
}
EXPERIMENTAL_BUILDERS = {
    "Album": {
        "builder": "scrapers/manufacturers/availability/album/build_album_us_availability.py",
        "status": "blocked",
        "reason": "Existing experiment still points at /en-au inventory and emits AUD pricing, so it is not safe to activate for RegionCode US.",
    }
}


def assert_region_scope() -> None:
    configured = os.getenv("QUIVRR_REGION_CODE", REGION_CODE).strip().upper()
    if configured != REGION_CODE:
        raise RuntimeError(
            f"US MFA pipeline refused QUIVRR_REGION_CODE={configured!r}; expected 'US'."
        )


def load_plan() -> dict:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if payload.get("regionCode") != REGION_CODE:
        raise RuntimeError("US MFA config is not region-scoped to US.")
    targets = payload.get("targets", [])
    names = {target.get("brandName") for target in targets}
    missing = [brand for brand in APPROVED_BRANDS if brand not in names]
    if missing:
        raise RuntimeError(f"US MFA plan is missing approved brands: {', '.join(missing)}")
    return payload


def build_rollout_report(payload: dict) -> dict:
    targets = payload.get("targets", [])
    brand_reports = []
    for target in targets:
        brand_name = target.get("brandName")
        experiment = EXPERIMENTAL_BUILDERS.get(brand_name)
        brand_reports.append({
            "brandName": brand_name,
            "sourceUrl": target.get("sourceUrl"),
            "builderStrategy": target.get("builderStrategy"),
            "enabled": bool(target.get("enabled")),
            "validated": bool(target.get("validated")),
            "status": experiment["status"] if experiment else "planned",
            "builder": experiment["builder"] if experiment else None,
            "reason": experiment["reason"] if experiment else target.get("marketNotes"),
        })
    return {
        "regionCode": REGION_CODE,
        "brandsPlanned": len(brand_reports),
        "brandsImplemented": sum(1 for brand in brand_reports if brand["status"] == "implemented"),
        "brandsBlocked": sum(1 for brand in brand_reports if brand["status"] == "blocked"),
        "brandsPlanningOnly": sum(1 for brand in brand_reports if brand["status"] == "planned"),
        "brands": brand_reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="US manufacturer availability planning scaffold. Phase 1 validates planning only and performs no SQL writes."
    )
    parser.add_argument("execution_mode", nargs="?", choices=["apply", "dry-run"])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Reserved for future US manufacturer availability apply mode.")
    mode.add_argument("--dry-run", action="store_true", help="Validate the US manufacturer availability plan without external fetches.")
    args = parser.parse_args()
    if args.execution_mode == "apply":
        args.apply = True
    elif args.execution_mode == "dry-run":
        args.dry_run = True

    assert_region_scope()
    emit_event("mfa_refresh_started", "manufacturer_availability", region=REGION_CODE, status="success")
    if args.apply:
        raise RuntimeError(
            "US manufacturer availability apply mode is intentionally disabled in Phase 1. "
            "This scaffold validates planning only and must not write SQL yet."
        )
    payload = load_plan()
    report = build_rollout_report(payload)
    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("US manufacturer availability planning dry-run complete")
    print(f"Brands planned: {len(payload.get('targets', []))}")
    print(f"Brands blocked pending source-safe builders: {report['brandsBlocked']}")
    print(f"Brands planning only: {report['brandsPlanningOnly']}")
    print(f"Report: {REPORT_OUTPUT}")
    update_job_state("mfa_us", "mfa", "manufacturer_availability", "success", region=REGION_CODE, rows=0)
    emit_event("mfa_refresh_completed", "manufacturer_availability", region=REGION_CODE, status="success", rows=0)


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
