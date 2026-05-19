import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]

PIPELINES = [
    {
        "name": "Channel Islands",
        "command": [
            sys.executable,
            "scrapers/brands/channel_islands/run_ci_pipeline.py",
        ],
    },
    {
        "name": "JS Industries",
        "command": [
            sys.executable,
            "scrapers/brands/run_js_pipeline.py",
        ],
    },
    {
        "name": "Pyzel",
        "command": [
            sys.executable,
            "scrapers/brands/run_pyzel_pipeline.py",
        ],
    },
    {
        "name": "DHD",
        "command": [
            sys.executable,
            "scrapers/brands/run_dhd_pipeline.py",
        ],
    },
    {
        "name": "Lost",
        "command": [
            sys.executable,
            "scrapers/brands/run_lost_pipeline.py",
        ],
    },
    {
        "name": "Rusty",
        "command": [
            sys.executable,
            "scrapers/brands/run_rusty_pipeline.py",
        ],
    },
    {
        "name": "Firewire",
        "command": [
            sys.executable,
            "scrapers/brands/run_firewire_pipeline.py",
        ],
    },
    {
        "name": "Haydenshapes",
        "command": [
            sys.executable,
            "scrapers/brands/run_haydenshapes_pipeline.py",
        ],
    },
    {
        "name": "Sharp Eye",
        "command": [
            sys.executable,
            "scrapers/brands/run_sharpeye_pipeline.py",
        ],
    },
    {
        "name": "Chilli",
        "command": [
            sys.executable,
            "scrapers/brands/run_chilli_pipeline.py",
        ],
    },

    {
        "name": "Album",
        "command": [
            sys.executable,
            "scrapers/brands/run_album_pipeline.py",
        ],
    },

    {
        "name": "Christenson",
        "command": [
            sys.executable,
            "scrapers/brands/run_christenson_pipeline.py",
        ],
    },


]

REPORT_PATH = Path("scrapers/brands/output/weekly_brand_catalogue_report.json")


def run_pipeline(pipeline):
    print("")
    print("#" * 100)
    print(f"RUNNING: {pipeline['name']}")
    print("#" * 100)

    command_path = ROOT / pipeline["command"][1]

    if not command_path.exists():
        raise RuntimeError(f"Missing pipeline file: {command_path}")

    started = datetime.now(timezone.utc)

    result = subprocess.run(
        pipeline["command"],
        cwd=ROOT,
        text=True,
    )

    ended = datetime.now(timezone.utc)

    row = {
        "brand": pipeline["name"],
        "command": " ".join(pipeline["command"]),
        "status": "succeeded" if result.returncode == 0 else "failed",
        "return_code": result.returncode,
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
    }

    if result.returncode != 0:
        raise RuntimeError(f"Pipeline failed: {pipeline['name']}")

    return row


def main():
    print("")
    print("Starting weekly manufacturer catalogue refresh")
    print("")

    results = []
    failed = False

    for pipeline in PIPELINES:
        try:
            results.append(run_pipeline(pipeline))
        except Exception as exc:
            failed = True
            results.append({
                "brand": pipeline["name"],
                "command": " ".join(pipeline["command"]),
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

    print("")
    print("Weekly manufacturer catalogue refresh complete")
    print("")


if __name__ == "__main__":
    main()
