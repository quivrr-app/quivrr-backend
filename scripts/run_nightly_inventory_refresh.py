from pathlib import Path
import json
import subprocess
import sys
import time
from datetime import datetime, timezone


OUTPUT_DIR = Path("scrapers/products/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JOB_REPORT_FILE = OUTPUT_DIR / "nightly_inventory_job_report.json"
ACTIVE_TARGETS_FILE = Path("scrapers/retailers/active_scrape_targets.json")


def utc_now():
    return datetime.now(timezone.utc)


def run_step(index, total, name, command, retry_count=0):
    print("")
    print(f"Step {index}/{total}")
    print(name)
    print("=" * 60)

    attempt = 0
    output_lines = []

    while attempt <= retry_count:
        attempt += 1

        if retry_count:
            print(f"Attempt {attempt}/{retry_count + 1}")

        started_at = utc_now()

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        if process.stdout:
            for line in process.stdout:
                print(line, end="")
                output_lines.append(line)

        return_code = process.wait()
        completed_at = utc_now()

        if return_code == 0:
            return {
                "step": index,
                "name": name,
                "command": command,
                "success": True,
                "return_code": return_code,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_seconds": int(
                    (completed_at - started_at).total_seconds()
                ),
                "output_tail": "".join(output_lines[-160:]),
            }

        if attempt <= retry_count:
            print("")
            print("Step failed. Retrying after 60 seconds...")
            time.sleep(60)

    return {
        "step": index,
        "name": name,
        "command": command,
        "success": False,
        "return_code": return_code,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": int(
            (completed_at - started_at).total_seconds()
        ),
        "output_tail": "".join(output_lines[-160:]),
    }


def active_target_count():
    if not ACTIVE_TARGETS_FILE.exists():
        return 0

    try:
        targets = json.loads(
            ACTIVE_TARGETS_FILE.read_text(encoding="utf-8")
        )
        return len(targets)
    except Exception:
        return 0


def main():
    print("")
    print("Quivrr nightly AU inventory job")
    print("=" * 60)

    started_at = utc_now()

    steps = [
        {
            "name": "Build active retailer targets",
            "command": [
                sys.executable,
                "-u",
                "scrapers/retailers/build_active_scrape_targets.py",
            ],
        },
        {
            "name": "Build retailer activation report",
            "command": [
                sys.executable,
                "-u",
                "scrapers/retailers/build_retailer_activation_report.py",
            ],
        },
        {
            "name": "Scrape Shopify retailers",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/shopify_scraper.py",
            ],
        },
        {
            "name": "Scrape WooCommerce retailers",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/woocommerce_scraper.py",
            ],
        },
        {
            "name": "Filter likely surfboards",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/filter_surfboards.py",
            ],
        },
        {
            "name": "Normalise surfboards",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/normalise_surfboards.py",
            ],
        },
        {
            "name": "Build grouped inventory index",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/build_grouped_inventory_index.py",
            ],
        },
        {
            "name": "Build JS inventory index",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/build_js_inventory_index.py",
            ],
        },
        {
            "name": "Build JS catalogue",
            "command": [
                sys.executable,
                "-u",
                "scrapers/brands/build_js_catalogue.py",
            ],
        },
        {
            "name": "Match JS inventory to catalogue",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/match_js_inventory_to_catalogue.py",
            ],
        },
        {
            "name": "Import available retailer inventory into Azure SQL",
            "command": [
                sys.executable,
                "-u",
                "scripts/import_retailer_inventory.py",
            ],
            "retry_count": 2,
        },
        {
            "name": "Build retailer scrape health report",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/build_retailer_quality_report.py",
            ],
        },
    ]

    results = []

    for index, step in enumerate(steps, start=1):
        result = run_step(
            index=index,
            total=len(steps),
            name=step["name"],
            command=step["command"],
            retry_count=step.get("retry_count", 0),
        )

        results.append(result)

        if not result["success"]:
            print("")
            print("Nightly inventory job stopped because a step failed.")
            print(f"Failed step: {step['name']}")
            break

    completed_at = utc_now()

    success = all(result["success"] for result in results)

    report = {
        "job_name": "quivrr-nightly-au-inventory-refresh",
        "success": success,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": int(
            (completed_at - started_at).total_seconds()
        ),
        "active_scrape_targets": active_target_count(),
        "steps": results,
    }

    JOB_REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("Quivrr nightly AU inventory job complete")
    print("=" * 60)
    print(f"Success: {success}")
    print(f"Duration: {report['duration_seconds']} seconds")
    print(f"Active scrape targets: {report['active_scrape_targets']}")
    print(f"Report: {JOB_REPORT_FILE}")

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
    