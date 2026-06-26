import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.structured_logging import emit_event, update_job_state

PYTHON = sys.executable

PIPELINES = [
    {
        "name": "JS Industries ID manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_js_id_availability_pipeline.py",
        ],
    }
]

def main():
    started = datetime.now(timezone.utc)
    perf_started = time.perf_counter()
    print(f"ID manufacturer availability pipeline started: {started.isoformat()}")
    emit_event("mfa_refresh_started", "manufacturer_availability", region="ID", status="success")

    failures = []

    for pipeline in PIPELINES:
        print("")
        print("=" * 100)
        print(pipeline["name"])
        print("=" * 100)
        emit_event("mfa_brand_started", "manufacturer_availability", region="ID", status="success", brand=pipeline["name"])

        result = subprocess.run(pipeline["command"])

        if result.returncode != 0:
            failures.append(pipeline["name"])
            emit_event("mfa_brand_failed", "manufacturer_availability", region="ID", status="failed", brand=pipeline["name"], error_type="PipelineExit", error_message=f"exit code {result.returncode}")
        else:
            emit_event("mfa_brand_completed", "manufacturer_availability", region="ID", status="success", brand=pipeline["name"])

    finished = datetime.now(timezone.utc)
    print("")
    print(f"ID manufacturer availability pipeline finished: {finished.isoformat()}")

    if failures:
        print("Failures:")
        for failure in failures:
            print(f"  {failure}")
        emit_event("mfa_refresh_failed", "manufacturer_availability", region="ID", status="failed", duration_seconds=round(time.perf_counter() - perf_started, 3))
        update_job_state("mfa_id", "mfa", "manufacturer_availability", "failed", region="ID", duration_seconds=round(time.perf_counter() - perf_started, 3))
        raise SystemExit(1)

    print("All ID manufacturer availability pipelines completed")
    emit_event("mfa_refresh_completed", "manufacturer_availability", region="ID", status="success", duration_seconds=round(time.perf_counter() - perf_started, 3))
    update_job_state("mfa_id", "mfa", "manufacturer_availability", "success", region="ID", duration_seconds=round(time.perf_counter() - perf_started, 3))

if __name__ == "__main__":
    main()
