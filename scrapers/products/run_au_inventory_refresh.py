from pathlib import Path
import json
import subprocess
import sys
from datetime import datetime, timezone

TARGETS_FILE = Path("scrapers/retailers/active_scrape_targets.json")
OUTPUT_DIR = Path("scrapers/products/output")
REPORT_FILE = OUTPUT_DIR / "au_inventory_refresh_report.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_step(name, script_path):
    print(f"\n{name}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, script_path],
        text=True,
        capture_output=True
    )

    print(result.stdout)

    if result.stderr:
        print(result.stderr)

    return {
        "name": name,
        "script_path": script_path,
        "return_code": result.returncode,
        "success": result.returncode == 0,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def main():
    if not TARGETS_FILE.exists():
        raise FileNotFoundError(
            f"Missing active scrape targets file: {TARGETS_FILE}"
        )

    targets = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))

    print("\nQuivrr AU inventory refresh")
    print("=" * 60)
    print(f"Active scrape targets: {len(targets)}")

    steps = [
        {
            "name": "Refresh surfboard inventory",
            "script_path": "scrapers/products/refresh_surfboard_inventory.py",
        },
        {
            "name": "Filter likely surfboards",
            "script_path": "scrapers/products/filter_surfboards.py",
        },
        {
            "name": "Normalise surfboards",
            "script_path": "scrapers/products/normalise_surfboards.py",
        },
        {
            "name": "Build grouped inventory index",
            "script_path": "scrapers/products/build_grouped_inventory_index.py",
        },
        {
            "name": "Build JS inventory index",
            "script_path": "scrapers/products/build_js_inventory_index.py",
        },
        {
            "name": "Build JS catalogue",
            "script_path": "scrapers/brands/build_js_catalogue.py",
        },
        {
            "name": "Match JS inventory to catalogue",
            "script_path": "scrapers/products/match_js_inventory_to_catalogue.py",
        },
    ]

    results = []

    for step in steps:
        results.append(
            run_step(
                step["name"],
                step["script_path"]
            )
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_scrape_targets": len(targets),
        "steps": results,
        "success": all(item["success"] for item in results),
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nAU inventory refresh complete")
    print("=" * 60)
    print(f"Success: {report['success']}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
    