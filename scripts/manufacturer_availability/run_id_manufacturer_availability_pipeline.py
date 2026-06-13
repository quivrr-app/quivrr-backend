import subprocess
import sys
from datetime import datetime, timezone

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
    print(f"ID manufacturer availability pipeline started: {started.isoformat()}")

    failures = []

    for pipeline in PIPELINES:
        print("")
        print("=" * 100)
        print(pipeline["name"])
        print("=" * 100)

        result = subprocess.run(pipeline["command"])

        if result.returncode != 0:
            failures.append(pipeline["name"])

    finished = datetime.now(timezone.utc)
    print("")
    print(f"ID manufacturer availability pipeline finished: {finished.isoformat()}")

    if failures:
        print("Failures:")
        for failure in failures:
            print(f"  {failure}")
        raise SystemExit(1)

    print("All ID manufacturer availability pipelines completed")

if __name__ == "__main__":
    main()
