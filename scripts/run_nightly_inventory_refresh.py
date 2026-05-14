from pathlib import Path
import json
import os
import smtplib
import subprocess
import sys
import time
from datetime import datetime, timezone
from email.message import EmailMessage


OUTPUT_DIR = Path("scrapers/products/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JOB_REPORT_FILE = OUTPUT_DIR / "nightly_inventory_job_report.json"
ACTIVE_TARGETS_FILE = Path("scrapers/retailers/active_scrape_targets.json")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp-mail.outlook.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "quivrr.platform@outlook.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_TO = os.getenv("NIGHTLY_REPORT_EMAIL_TO", "dunn.nathan@hotmail.com")
EMAIL_FROM = os.getenv("NIGHTLY_REPORT_EMAIL_FROM", SMTP_USERNAME)


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


def load_json_file(file_path):
    if not file_path.exists():
        return None

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_email_body(report):
    quality_report = load_json_file(
        OUTPUT_DIR / "inventory_quality_report.json"
    )

    grouped_inventory = load_json_file(
        OUTPUT_DIR / "grouped_inventory_index.json"
    )

    js_inventory = load_json_file(
        OUTPUT_DIR / "js_inventory_index.json"
    )

    successful_steps = [
        step for step in report["steps"]
        if step.get("success")
    ]

    failed_steps = [
        step for step in report["steps"]
        if not step.get("success")
    ]

    lines = [
        "Quivrr nightly AU retailer inventory report",
        "",
        f"Status: {'Succeeded' if report['success'] else 'Failed'}",
        f"Started UTC: {report['started_at']}",
        f"Completed UTC: {report['completed_at']}",
        f"Duration seconds: {report['duration_seconds']}",
        f"Active scrape targets: {report['active_scrape_targets']}",
        f"Steps completed: {len(successful_steps)}/{len(report['steps'])}",
        "",
    ]

    if quality_report:
        lines.extend([
            "Inventory quality",
            f"Total records: {quality_report.get('total_records', 'n/a')}",
            f"With length: {quality_report.get('with_length', 'n/a')}",
            f"With volume: {quality_report.get('with_volume', 'n/a')}",
            f"Available: {quality_report.get('available', 'n/a')}",
            f"Retailers: {quality_report.get('retailers', 'n/a')}",
            "",
        ])

    if isinstance(grouped_inventory, list):
        lines.append(f"Grouped inventory records: {len(grouped_inventory)}")
    elif isinstance(grouped_inventory, dict):
        lines.append(f"Grouped inventory keys: {len(grouped_inventory)}")

    if isinstance(js_inventory, list):
        lines.append(f"JS inventory records: {len(js_inventory)}")
    elif isinstance(js_inventory, dict):
        lines.append(f"JS inventory keys: {len(js_inventory)}")

    lines.append("")

    if failed_steps:
        lines.append("Failed steps")
        for step in failed_steps:
            lines.append(f"- {step['name']}")
            lines.append(step.get("output_tail", "")[-2000:])
            lines.append("")
    else:
        lines.append("All steps completed successfully.")

    lines.append("")
    lines.append("Step summary")

    for step in report["steps"]:
        status = "OK" if step.get("success") else "FAILED"
        lines.append(
            f"- {status}: {step['name']} "
            f"({step.get('duration_seconds', 0)} seconds)"
        )

    return "\n".join(lines)


def send_email_report(report):
    if not SMTP_PASSWORD:
        print("")
        print("Email report skipped. SMTP_PASSWORD is not configured.")
        return

    subject_status = "Succeeded" if report["success"] else "Failed"

    message = EmailMessage()
    message["Subject"] = f"Quivrr nightly inventory report: {subject_status}"
    message["From"] = EMAIL_FROM
    message["To"] = EMAIL_TO
    message.set_content(build_email_body(report))

    message.add_attachment(
        JOB_REPORT_FILE.read_bytes(),
        maintype="application",
        subtype="json",
        filename=JOB_REPORT_FILE.name,
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)

    print("")
    print(f"Email report sent to {EMAIL_TO}")


def main():
    print("")
    print("Quivrr nightly AU retailer inventory job")
    print("=" * 60)

    started_at = utc_now()

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

    try:
        send_email_report(report)
    except Exception as exc:
        print("")
        print(f"Email report failed: {exc}")

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()