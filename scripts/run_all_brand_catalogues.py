import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from utils.structured_logging import emit_event, update_job_state


PYTHON = sys.executable

STEPS = [
    {
        "name": "JS Industries",
        "command": [PYTHON, "scrapers/brands/run_js_pipeline.py"],
    },
    {
        "name": "Channel Islands",
        "command": [PYTHON, "scrapers/brands/channel_islands/run_ci_pipeline.py"],
    },
    {
        "name": "Pyzel",
        "command": [PYTHON, "scripts/run_pyzel_pipeline.py"],
    },
    {
        "name": "DHD",
        "command": [PYTHON, "scripts/run_dhd_pipeline.py"],
    },
    {
        "name": "Lost",
        "command": [PYTHON, "scripts/run_lost_pipeline.py"],
    },
    {
        "name": "Rusty",
        "command": [PYTHON, "scripts/run_rusty_pipeline.py"],
    },
    {
        "name": "Firewire",
        "command": [PYTHON, "scripts/run_firewire_pipeline.py"],
    },
    {
        "name": "Haydenshapes",
        "command": [PYTHON, "scripts/run_haydenshapes_pipeline.py"],
    },
    {
        "name": "Sharp Eye",
        "command": [PYTHON, "scripts/run_sharpeye_pipeline.py"],
    },
    {
        "name": "Misfit Shapes",
        "command": [PYTHON, "scripts/run_misfit_pipeline.py"],
    },
    {
        "name": "Chemistry Surfboards",
        "command": [PYTHON, "scripts/run_chemistry_pipeline.py"],
    },
    {
        "name": "Pukas",
        "command": [PYTHON, "scripts/run_pukas_pipeline.py"],
    },
    {
        "name": "Simon Anderson",
        "command": [PYTHON, "scripts/run_simon_anderson_pipeline.py"],
    },
    {
        "name": "Chilli",
        "command": [PYTHON, "scripts/run_chilli_pipeline.py"],
    },
    {
        "name": "Album",
        "command": [PYTHON, "scripts/run_album_pipeline.py"],
    },
    {
        "name": "Christenson",
        "command": [PYTHON, "scripts/run_christenson_pipeline.py"],
    },
]

REPORT_PATH = Path("scrapers/brands/output/weekly_brand_catalogue_report.json")

POST_CATALOGUE_STEPS = [
    {
        "name": "AU Manufacturer Direct Availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py",
        ],
    },
]


def run_step(step):
    command_path = Path(step["command"][1])

    if not command_path.exists():
        raise RuntimeError(f"Missing pipeline file: {command_path}")

    print("")
    print("=" * 80)
    print(f"Running brand pipeline: {step['name']}")
    print("=" * 80)
    print(" ".join(step["command"]))
    print("")

    started = datetime.now(timezone.utc)

    result = subprocess.run(step["command"])

    ended = datetime.now(timezone.utc)

    row = {
        "brand": step["name"],
        "command": " ".join(step["command"]),
        "status": "succeeded" if result.returncode == 0 else "failed",
        "return_code": result.returncode,
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
    }

    if result.returncode != 0:
        raise RuntimeError(f"{step['name']} pipeline failed")

    return row


def main():
    started = time.perf_counter()
    emit_event("catalogue_refresh_started", "brand_catalogue", status="success")
    results = []
    failed = False

    for step in STEPS:
        try:
            emit_event("catalogue_brand_started", "brand_catalogue", status="success", brand=step["name"])
            results.append(run_step(step))
            emit_event("catalogue_brand_completed", "brand_catalogue", status="success", brand=step["name"])
        except Exception as exc:
            failed = True
            results.append({
                "brand": step["name"],
                "status": "failed",
                "message": str(exc),
                "ended_at_utc": datetime.now(timezone.utc).isoformat(),
            })
            emit_event(
                "catalogue_brand_failed",
                "brand_catalogue",
                status="failed",
                brand=step["name"],
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            break

    if not failed:
        for post_step in POST_CATALOGUE_STEPS:
            try:
                emit_event("catalogue_brand_started", "brand_catalogue", status="success", brand=post_step["name"])
                results.append(run_step(post_step))
                emit_event("catalogue_brand_completed", "brand_catalogue", status="success", brand=post_step["name"])
            except Exception as exc:
                failed = True
                results.append({
                    "brand": post_step["name"],
                    "status": "failed",
                    "message": str(exc),
                    "ended_at_utc": datetime.now(timezone.utc).isoformat(),
                })
                emit_event(
                    "catalogue_brand_failed",
                    "brand_catalogue",
                    status="failed",
                    brand=post_step["name"],
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                break

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    REPORT_PATH.write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "failed" if failed else "succeeded",
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print(f"Weekly brand catalogue report: {REPORT_PATH}")
    print("")

    if failed:
        emit_event("catalogue_refresh_failed", "brand_catalogue", status="failed", duration_seconds=round(time.perf_counter() - started, 3))
        update_job_state("weekly_brand_catalogues", "catalogue", "brand_catalogue", "failed", duration_seconds=round(time.perf_counter() - started, 3))
        sys.exit(1)
    emit_event("catalogue_refresh_completed", "brand_catalogue", status="success", duration_seconds=round(time.perf_counter() - started, 3), row_count=len(results))
    update_job_state("weekly_brand_catalogues", "catalogue", "brand_catalogue", "success", duration_seconds=round(time.perf_counter() - started, 3), row_count=len(results))


if __name__ == "__main__":
    main()

