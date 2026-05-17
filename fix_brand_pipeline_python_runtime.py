from pathlib import Path

files = {}

files["scripts/run_pyzel_pipeline.py"] = r'''
import subprocess
import sys


PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/pyzel/build_pyzel_master_catalogue.py"],
    [PYTHON, "scripts/import_pyzel_catalogue.py"],
]


def run_step(command):
    print("")
    print("=" * 80)
    print("Running:", " ".join(command))
    print("=" * 80)
    print("")

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {' '.join(command)}")


def main():
    for step in STEPS:
        run_step(step)

    print("")
    print("Pyzel catalogue pipeline complete")
    print("")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print(f"Pyzel catalogue pipeline failed: {exc}")
        print("")
        sys.exit(1)
'''

files["scripts/run_dhd_pipeline.py"] = r'''
import subprocess
import sys


PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/dhd/build_dhd_master_catalogue.py"],
    [PYTHON, "scripts/import_dhd_catalogue.py"],
]


def run_step(command):
    print("")
    print("=" * 80)
    print("Running:", " ".join(command))
    print("=" * 80)
    print("")

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {' '.join(command)}")


def main():
    for step in STEPS:
        run_step(step)

    print("")
    print("DHD catalogue pipeline complete")
    print("")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print(f"DHD catalogue pipeline failed: {exc}")
        print("")
        sys.exit(1)
'''

files["scripts/run_all_brand_catalogues.py"] = r'''
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PYTHON = sys.executable

STEPS = [
    {
        "name": "JS Industries",
        "command": [PYTHON, "scripts/run_js_pipeline.py"],
        "required": False,
    },
    {
        "name": "Channel Islands",
        "command": [PYTHON, "scripts/run_ci_pipeline.py"],
        "required": False,
    },
    {
        "name": "Pyzel",
        "command": [PYTHON, "scripts/run_pyzel_pipeline.py"],
        "required": True,
    },
    {
        "name": "DHD",
        "command": [PYTHON, "scripts/run_dhd_pipeline.py"],
        "required": True,
    },
]


REPORT_PATH = Path("scrapers/brands/output/weekly_brand_catalogue_report.json")


def run_step(step):
    command_path = Path(step["command"][1])

    if not command_path.exists():
        message = f"Missing pipeline file: {command_path}"

        if step["required"]:
            raise RuntimeError(message)

        return {
            "brand": step["name"],
            "status": "skipped",
            "message": message,
        }

    print("")
    print("=" * 80)
    print(f"Running brand pipeline: {step['name']}")
    print("=" * 80)
    print(" ".join(step["command"]))
    print("")

    started = datetime.now(timezone.utc)
    result = subprocess.run(step["command"])
    ended = datetime.now(timezone.utc)

    status = "succeeded" if result.returncode == 0 else "failed"

    row = {
        "brand": step["name"],
        "command": " ".join(step["command"]),
        "status": status,
        "return_code": result.returncode,
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
    }

    if result.returncode != 0 and step["required"]:
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
        __import__("json").dumps(
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

for path, content in files.items():
    Path(path).write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Updated {path}")
