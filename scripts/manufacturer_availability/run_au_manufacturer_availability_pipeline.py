import subprocess
import sys
from datetime import datetime, timezone

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
    print("")
    print("Running AU manufacturer direct availability pipeline")
    print("=" * 100)
    print(f"UTC start: {datetime.now(timezone.utc).isoformat()}")

    failures = []

    for pipeline in PIPELINES:
        exit_code = run_step(
            pipeline["name"],
            pipeline["command"],
        )

        if exit_code != 0:
            failures.append({
                "name": pipeline["name"],
                "exitCode": exit_code,
            })

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

        sys.exit(1)

if __name__ == "__main__":
    main()
