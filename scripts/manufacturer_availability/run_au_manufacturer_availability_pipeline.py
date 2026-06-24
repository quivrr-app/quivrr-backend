import subprocess
import sys
import time
from datetime import datetime, timezone

from utils.structured_logging import emit_event, update_job_state

PYTHON = sys.executable

PIPELINES = [
    {
        "name": "JS Industries AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_js_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Album AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_album_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Channel Islands AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_ci_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Chemistry Surfboards AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_chemistry_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Chilli AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_chilli_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Christenson AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_christenson_au_availability_pipeline.py",
        ],
    },
    {
        "name": "DHD AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_dhd_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Pyzel AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_pyzel_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Firewire AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_firewire_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Lost AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_lost_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Sharp Eye AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_sharpeye_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Haydenshapes AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_haydenshapes_au_availability_pipeline.py",
        ],
    },
    {
        "name": "Misfit Shapes AU manufacturer availability",
        "command": [
            PYTHON,
            "scripts/manufacturer_availability/run_misfit_au_availability_pipeline.py",
        ],
    },
]


def run_step(name, command):
    print("")
    print("=" * 100)
    print(f"Starting: {name}")
    print(f"UTC: {datetime.now(timezone.utc).isoformat()}")
    print("Command:", " ".join(command))
    print("=" * 100)

    result = subprocess.run(command)

    if result.returncode != 0:
        print("")
        print(f"FAILED: {name}")
        print(f"Exit code: {result.returncode}")
        return result.returncode

    print("")
    print(f"Completed: {name}")
    return 0


def main():
    started = time.perf_counter()
    print("")
    print("Running AU manufacturer direct availability pipeline")
    print("=" * 100)
    print(f"UTC start: {datetime.now(timezone.utc).isoformat()}")
    emit_event("mfa_refresh_started", "manufacturer_availability", region="AU", status="success")

    failures = []

    for pipeline in PIPELINES:
        emit_event("mfa_brand_started", "manufacturer_availability", region="AU", status="success", brand=pipeline["name"])
        exit_code = run_step(
            pipeline["name"],
            pipeline["command"],
        )

        if exit_code != 0:
            failures.append({
                "name": pipeline["name"],
                "exitCode": exit_code,
            })
            emit_event(
                "mfa_brand_failed",
                "manufacturer_availability",
                region="AU",
                status="failed",
                brand=pipeline["name"],
                error_type="PipelineExit",
                error_message=f"exit code {exit_code}",
            )
        else:
            emit_event(
                "mfa_brand_completed",
                "manufacturer_availability",
                region="AU",
                status="success",
                brand=pipeline["name"],
            )

    print("")
    print("=" * 100)
    print("AU manufacturer direct availability pipeline complete")
    print(f"UTC end: {datetime.now(timezone.utc).isoformat()}")
    print(f"Total pipelines: {len(PIPELINES)}")
    print(f"Failures: {len(failures)}")
    print("=" * 100)

    if failures:
        for failure in failures:
            print(f"FAILED: {failure['name']} exitCode={failure['exitCode']}")
        emit_event("mfa_refresh_failed", "manufacturer_availability", region="AU", status="failed", duration_seconds=round(time.perf_counter() - started, 3))
        update_job_state("mfa_au", "mfa", "manufacturer_availability", "failed", region="AU", duration_seconds=round(time.perf_counter() - started, 3))
        sys.exit(1)
    emit_event("mfa_refresh_completed", "manufacturer_availability", region="AU", status="success", duration_seconds=round(time.perf_counter() - started, 3))
    update_job_state("mfa_au", "mfa", "manufacturer_availability", "success", region="AU", duration_seconds=round(time.perf_counter() - started, 3))


if __name__ == "__main__":
    main()
