import json
import os
import subprocess
import sys
import time
import traceback
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
TAIL_LINE_LIMIT = 40


class StepExecutionError(RuntimeError):
    def __init__(self, message, row):
        super().__init__(message)
        self.row = row


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
    output_tail = deque(maxlen=TAIL_LINE_LIMIT)

    environment = dict(os.environ)
    environment.setdefault("PYTHONUNBUFFERED", "1")
    process = subprocess.Popen(
        step["command"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=environment,
    )

    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        output_tail.append(line.rstrip())

    return_code = process.wait()
    ended = datetime.now(timezone.utc)

    row = {
        "brand": step["name"],
        "command": " ".join(step["command"]),
        "pipeline_path": str(command_path),
        "status": "succeeded" if return_code == 0 else "failed",
        "return_code": return_code,
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
        "duration_seconds": round((ended - started).total_seconds(), 3),
        "output_tail": list(output_tail),
    }

    if return_code != 0:
        raise StepExecutionError(f"{step['name']} pipeline failed", row)

    return row


def main():
    started = time.perf_counter()
    emit_event("catalogue_refresh_started", "brand_catalogue", status="success")
    results = []
    failures = []

    for step in STEPS:
        try:
            emit_event("catalogue_brand_started", "brand_catalogue", status="success", brand=step["name"])
            row = run_step(step)
            results.append(row)
            emit_event(
                "catalogue_brand_completed",
                "brand_catalogue",
                status="success",
                brand=step["name"],
                command=row["command"],
                pipeline_path=row["pipeline_path"],
                exit_code=row["return_code"],
                duration_seconds=row["duration_seconds"],
            )
        except Exception as exc:
            failures.append(step["name"])
            failed_row = getattr(exc, "row", None) or {
                "brand": step["name"],
                "command": " ".join(step["command"]),
                "pipeline_path": str(Path(step["command"][1])),
                "status": "failed",
                "message": str(exc),
                "return_code": None,
                "ended_at_utc": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": None,
                "output_tail": [],
            }
            failed_row["traceback"] = traceback.format_exc()
            results.append(failed_row)
            emit_event(
                "catalogue_brand_failed",
                "brand_catalogue",
                status="failed",
                brand=step["name"],
                command=failed_row.get("command"),
                pipeline_path=failed_row.get("pipeline_path"),
                exit_code=failed_row.get("return_code"),
                duration_seconds=failed_row.get("duration_seconds"),
                error_type=type(exc).__name__,
                error_message=str(exc),
                output_tail=failed_row.get("output_tail", []),
                traceback=failed_row.get("traceback"),
            )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    duration_seconds = round(time.perf_counter() - started, 3)
    successful_brands = [row["brand"] for row in results if row.get("status") == "succeeded"]

    REPORT_PATH.write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "failed" if failures else "succeeded",
                "total_brands": len(STEPS),
                "successful_brand_count": len(successful_brands),
                "failed_brand_count": len(failures),
                "failed_brands": failures,
                "succeeded_brands": successful_brands,
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print(f"Weekly brand catalogue report: {REPORT_PATH}")
    print(f"Completed brands: {len(successful_brands)}/{len(STEPS)}")
    if failures:
        print(f"Failed brands: {', '.join(failures)}")
    print("")

    if failures:
        emit_event(
            "catalogue_refresh_failed",
            "brand_catalogue",
            status="failed",
            duration_seconds=duration_seconds,
            total_brand_count=len(STEPS),
            successful_brand_count=len(successful_brands),
            failed_brand_count=len(failures),
            failed_brands=failures,
            row_count=len(results),
        )
        update_job_state(
            "weekly_brand_catalogues",
            "catalogue",
            "brand_catalogue",
            "failed",
            duration_seconds=duration_seconds,
            total_brand_count=len(STEPS),
            successful_brand_count=len(successful_brands),
            failed_brand_count=len(failures),
            failed_brands=failures,
            row_count=len(results),
        )
        sys.exit(1)
    emit_event(
        "catalogue_refresh_completed",
        "brand_catalogue",
        status="success",
        duration_seconds=duration_seconds,
        total_brand_count=len(STEPS),
        successful_brand_count=len(successful_brands),
        row_count=len(results),
    )
    update_job_state(
        "weekly_brand_catalogues",
        "catalogue",
        "brand_catalogue",
        "success",
        duration_seconds=duration_seconds,
        total_brand_count=len(STEPS),
        successful_brand_count=len(successful_brands),
        row_count=len(results),
    )


if __name__ == "__main__":
    main()

