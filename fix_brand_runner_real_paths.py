from pathlib import Path

path = Path("scripts/run_all_brand_catalogues.py")

content = r'''
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


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
]

REPORT_PATH = Path("scrapers/brands/output/weekly_brand_catalogue_report.json")


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
    results = []
    failed = False

    for step in STEPS:
        try:
            results.append(run_step(step))
        except Exception as exc:
            failed = True
            results.append({
                "brand": step["name"],
                "status": "failed",
                "message": str(exc),
                "ended_at_utc": datetime.now(timezone.utc).isoformat(),
            })
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
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

path.write_text(content.strip() + "\n", encoding="utf-8")

print(f"Updated {path}")
