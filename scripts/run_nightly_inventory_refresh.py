from pathlib import Path
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.structured_logging import emit_event, update_job_state

PYTHON = sys.executable


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


def parse_count(pattern, text):
    match = re.search(pattern, text or "", re.IGNORECASE)
    return int(match.group(1)) if match else None


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
    print("Quivrr nightly AU retailer inventory job")
    print("=" * 60)

    started_at = utc_now()
    emit_event("inventory_refresh_started", "retailer_inventory", region="AU", status="success")

    steps = [
        {
            "name": "Detect retailer platforms",
            "command": [
                sys.executable,
                "-u",
                "scrapers/retailers/detect_retailer_platforms.py",
            ],
            "retry_count": 1,
        },
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
            "retry_count": 1,
        },
        {
            "name": "Scrape WooCommerce retailers",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/woocommerce_scraper.py",
            ],
            "retry_count": 1,
        },
        {
            "name": "Scrape BigCommerce retailers",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/bigcommerce_scraper.py",
            ],
            "retry_count": 1,
        },
        {
            "name": "Scrape Magento retailers",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/magento_scraper.py",
            ],
            "retry_count": 1,
        },
        {
            "name": "Scrape Neto Maropost retailers",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/neto_maropost_scraper.py",
            ],
            "retry_count": 1,
        },
        {
            "name": "Scrape Squarespace retailers",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/squarespace_scraper.py",
            ],
            "retry_count": 1,
        },
        {
            "name": "Scrape Wix retailers",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/wix_scraper.py",
            ],
            "retry_count": 1,
        },
        {
            "name": "Scrape Ecwid retailers",
            "command": [
                sys.executable,
                "-u",
                "scrapers/products/ecwid_scraper.py",
            ],
            "retry_count": 1,
        },
        {
            "name": "Scrape Coopers Board Store",
            "command": [
                sys.executable,
                "-u",
                "scrapers/retailers/scrape_coopers_inventory.py",
            ],
            "retry_count": 1,
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
            "name": "Import available retailer inventory into Azure SQL",
            "command": [
                sys.executable,
                "-u",
                "scripts/import_retailer_inventory.py",
            ],
            "retry_count": 2,
        },
    {
        "name": "Import Slimes Newcastle dedicated inventory",
        "command": [
            PYTHON,
            "scripts/import_slimes_newcastle_inventory.py",
        ],
        "required": False,
        "attempts": 2,
    },
        {
            "name": "Reconcile retailer inventory brands",
            "command": [
                sys.executable,
                "-u",
                "scripts/reconcile_retailer_inventory_brands.py",
            ],
            "retry_count": 1,
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
        if step["name"].startswith("Scrape "):
            emit_event(
                "retailer_scrape_started",
                "retailer_inventory",
                region="AU",
                status="success",
                retailer=step["name"].replace("Scrape ", ""),
            )
        result = run_step(
            index=index,
            total=len(steps),
            name=step["name"],
            command=step["command"],
            retry_count=step.get("retry_count", 0),
        )

        results.append(result)
        output_tail = result.get("output_tail") or ""
        if step["name"].startswith("Scrape "):
            emit_event(
                "retailer_scrape_completed",
                "retailer_inventory",
                region="AU",
                status="success" if result["success"] else "failed",
                retailer=step["name"].replace("Scrape ", ""),
                duration_seconds=result["duration_seconds"],
            )
        if step["name"] == "Import available retailer inventory into Azure SQL":
            emit_event(
                "inventory_import_completed",
                "retailer_inventory",
                region="AU",
                status="success" if result["success"] else "failed",
                rows_loaded=parse_count(r"Rows loaded:\s*(\d+)", output_tail),
                rows_inserted=parse_count(r"Available inventory rows inserted:\s*(\d+)", output_tail),
                duration_seconds=result["duration_seconds"],
            )

        if not result["success"]:
            print("")
            print("Nightly inventory job stopped because a step failed.")
            print(f"Failed step: {step['name']}")
            emit_event(
                "inventory_refresh_failed",
                "retailer_inventory",
                region="AU",
                status="failed",
                error_type="StepFailure",
                error_message=step["name"],
                duration_seconds=result["duration_seconds"],
            )
            break

    completed_at = utc_now()

    success = all(result["success"] for result in results)

    report = {
        "job_name": "quivrr-nightly-au-retailer-inventory",
        "success": success,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": int(
            (completed_at - started_at).total_seconds()
        ),
        "active_scrape_targets": active_target_count(),
        "steps": results,
    }

    emit_event(
        "inventory_linking_completed",
        "retailer_inventory",
        region="AU",
        status="success" if success else "failed",
        duration_seconds=int((completed_at - started_at).total_seconds()),
    )
    final_event = "inventory_refresh_completed" if success else "inventory_refresh_failed"
    emit_event(
        final_event,
        "retailer_inventory",
        region="AU",
        status="success" if success else "failed",
        duration_seconds=report["duration_seconds"],
        rows_loaded=None,
        rows_inserted=None,
    )
    update_job_state(
        "inventory_au",
        "inventory",
        "retailer_inventory",
        "success" if success else "failed",
        region="AU",
        duration_seconds=report["duration_seconds"],
        active_scrape_targets=report["active_scrape_targets"],
    )

    JOB_REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("Quivrr nightly AU retailer inventory job complete")
    print("=" * 60)
    print(f"Success: {success}")
    print(f"Duration: {report['duration_seconds']} seconds")
    print(f"Active scrape targets: {report['active_scrape_targets']}")
    print(f"Report: {JOB_REPORT_FILE}")

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
    
