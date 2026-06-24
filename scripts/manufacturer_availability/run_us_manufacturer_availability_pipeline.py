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
    print("US manufacturer availability planning dry-run complete")
    print(f"Brands planned: {len(payload.get('targets', []))}")
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
