from pathlib import Path
import json
import subprocess
import sys
from datetime import datetime, timezone


TARGETS_FILE = Path("scrapers/retailers/active_scrape_targets.json")
OUTPUT_DIR = Path("scrapers/products/output")
REPORT_FILE = OUTPUT_DIR / "au_inventory_refresh_report.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_step(index, total, name, script_path):
    print("")
    print(f"Step {index}/{total}")
    print(name)
    print("=" * 60)

    started_at = datetime.now(timezone.utc)

    process = subprocess.Popen(
        [sys.executable, "-u", script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines = []

    if process.stdout:
        for line in process.stdout:
            print(line, end="")
            output_lines.append(line)

    return_code = process.wait()

    completed_at = datetime.now(timezone.utc)

    return {
        "step": index,
        "name": name,
        "script_path": script_path,
        "return_code": return_code,
        "success": return_code == 0,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": int(
            (completed_at - started_at).total_seconds()
        ),
        "output_tail": "".join(output_lines[-120:]),
    }


def load_active_target_count():
    if not TARGETS_FILE.exists():
        return 0

    try:
        targets = json.loads(
            TARGETS_FILE.read_text(encoding="utf-8")
        )

        return len(targets)

    except Exception:
        return 0


def main():
    print("")
    print("Quivrr AU inventory refresh")
    print("=" * 60)

    steps = [
        {
            "name": "Build active retailer targets",
            "script_path": "scrapers/retailers/build_active_scrape_targets.py",
        },
        {
            "name": "Build retailer activation report",
            "script_path": "scrapers/retailers/build_retailer_activation_report.py",
        },
        {
            "name": "Scrape Shopify retailers",
            "script_path": "scrapers/products/shopify_scraper.py",
        },
        {
            "name": "Scrape WooCommerce retailers",
            "script_path": "scrapers/products/woocommerce_scraper.py",
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
        {
            "name": "Import available retailer inventory into Azure SQL",
            "script_path": "scripts/import_retailer_inventory.py",
        },
        {
            "name": "Build retailer scrape health report",
            "script_path": "scrapers/products/build_retailer_quality_report.py",
        },
    ]

    total_steps = len(steps)

    results = []

    started_at = datetime.now(timezone.utc)

    for index, step in enumerate(steps, start=1):
        result = run_step(
            index=index,
            total=total_steps,
            name=step["name"],
            script_path=step["script_path"],
        )

        results.append(result)

        if not result["success"]:
            print("")
            print("Pipeline stopped because a step failed.")
            print(f"Failed step: {step['name']}")
            break

    completed_at = datetime.now(timezone.utc)

    success = all(item["success"] for item in results)

    report = {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": int(
            (completed_at - started_at).total_seconds()
        ),
        "success": success,
        "active_scrape_targets": load_active_target_count(),
        "steps": results,
    }

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("AU inventory refresh complete")
    print("=" * 60)
    print(f"Success: {success}")
    print(f"Duration: {report['duration_seconds']} seconds")
    print(
        f"Active scrape targets: "
        f"{report['active_scrape_targets']}"
    )
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()