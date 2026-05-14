from pathlib import Path
import json
import os
import ssl
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
QUALITY_REPORT_FILE = OUTPUT_DIR / "inventory_quality_report.json"


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
                "duration_seconds": int((completed_at - started_at).total_seconds()),
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
        "duration_seconds": int((completed_at - started_at).total_seconds()),
        "output_tail": "".join(output_lines[-160:]),
    }


def active_target_count():
    if not ACTIVE_TARGETS_FILE.exists():
        return 0

    try:
        targets = json.loads(ACTIVE_TARGETS_FILE.read_text(encoding="utf-8"))
        return len(targets)
    except Exception:
        return 0


def read_json_file(path):
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def extract_quality_summary():
    quality = read_json_file(QUALITY_REPORT_FILE)

    if not quality:
        return {}

    return {
        "total_records": quality.get("total_records"),
        "available": quality.get("available"),
        "retailers": quality.get("retailers"),
        "with_length": quality.get("with_length"),
        "with_volume": quality.get("with_volume"),
    }


def build_email_body(report):
    failed_steps = [
        step for step in report["steps"]
        if not step["success"]
    ]

    quality = extract_quality_summary()

    lines = [
        "Quivrr nightly AU inventory refresh complete.",
        "",
        f"Status: {'SUCCESS' if report['success'] else 'FAILED'}",
        f"Started UTC: {report['started_at']}",
        f"Completed UTC: {report['completed_at']}",
        f"Duration seconds: {report['duration_seconds']}",
        f"Active scrape targets: {report['active_scrape_targets']}",
        "",
    ]

    if quality:
        lines.extend([
            "Inventory summary:",
            f"Total normalised records: {quality.get('total_records')}",
            f"Available records: {quality.get('available')}",
            f"Retailers with records: {quality.get('retailers')}",
            f"Records with length: {quality.get('with_length')}",
            f"Records with volume: {quality.get('with_volume')}",
            "",
        ])

    lines.append("Step summary:")

    for step in report["steps"]:
        status = "OK" if step["success"] else "FAILED"
        lines.append(
            f"{step['step']}. {status} | {step['name']} | {step['duration_seconds']}s"
        )

    if failed_steps:
        lines.append("")
        lines.append("Failed step output:")
        lines.append(failed_steps[0].get("output_tail", ""))

    lines.append("")
    lines.append(f"Report file: {JOB_REPORT_FILE}")

    return "\n".join(lines)


def send_email_report(report):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("EMAIL_FROM")
    email_to = os.getenv("EMAIL_TO")

    if not all([smtp_host, smtp_username, smtp_password, email_from, email_to]):
        print("")
        print("Email report skipped. SMTP or email environment variables are not configured.")
        return

    subject_status = "SUCCESS" if report["success"] else "FAILED"

    message = EmailMessage()
    message["Subject"] = f"Quivrr nightly AU inventory job: {subject_status}"
    message["From"] = email_from
    message["To"] = email_to
    message.set_content(build_email_body(report))

    context = ssl.create_default_context()

    with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as server:
        server.starttls(context=context)
        server.login(smtp_username, smtp_password)
        server.send_message(message)

    print("")
    print(f"Email report sent to {email_to}")


def main():
    print("")
    print("Quivrr nightly AU retailer inventory job")
    print("=" * 60)

    started_at = utc_now()

    steps = [
        {
            "name": "Detect retailer platforms",
            "command": [sys.executable, "-u", "scrapers/retailers/detect_retailer_platforms.py"],
            "retry_count": 1,
        },
        {
            "name": "Build active retailer targets",
            "command": [sys.executable, "-u", "scrapers/retailers/build_active_scrape_targets.py"],
        },
        {
            "name": "Build retailer activation report",
            "command": [sys.executable, "-u", "scrapers/retailers/build_retailer_activation_report.py"],
        },
        {
            "name": "Scrape Shopify retailers",
            "command": [sys.executable, "-u", "scrapers/products/shopify_scraper.py"],
            "retry_count": 1,
        },
        {
            "name": "Scrape WooCommerce retailers",
            "command": [sys.executable, "-u", "scrapers/products/woocommerce_scraper.py"],
            "retry_count": 1,
        },
        {
            "name": "Scrape BigCommerce retailers",
            "command": [sys.executable, "-u", "scrapers/products/bigcommerce_scraper.py"],
            "retry_count": 1,
        },
        {
            "name": "Scrape Magento retailers",
            "command": [sys.executable, "-u", "scrapers/products/magento_scraper.py"],
            "retry_count": 1,
        },
        {
            "name": "Scrape Neto Maropost retailers",
            "command": [sys.executable, "-u", "scrapers/products/neto_maropost_scraper.py"],
            "retry_count": 1,
        },
        {
            "name": "Scrape Squarespace retailers",
            "command": [sys.executable, "-u", "scrapers/products/squarespace_scraper.py"],
            "retry_count": 1,
        },
        {
            "name": "Scrape Wix retailers",
            "command": [sys.executable, "-u", "scrapers/products/wix_scraper.py"],
            "retry_count": 1,
        },
        {
            "name": "Scrape Ecwid retailers",
            "command": [sys.executable, "-u", "scrapers/products/ecwid_scraper.py"],
            "retry_count": 1,
        },
        {
            "name": "Filter likely surfboards",
            "command": [sys.executable, "-u", "scrapers/products/filter_surfboards.py"],
        },
        {
            "name": "Normalise surfboards",
            "command": [sys.executable, "-u", "scrapers/products/normalise_surfboards.py"],
        },
        {
            "name": "Build grouped inventory index",
            "command": [sys.executable, "-u", "scrapers/products/build_grouped_inventory_index.py"],
        },
        {
            "name": "Build JS inventory index",
            "command": [sys.executable, "-u", "scrapers/products/build_js_inventory_index.py"],
        },
        {
            "name": "Import available retailer inventory into Azure SQL",
            "command": [sys.executable, "-u", "scripts/import_retailer_inventory.py"],
            "retry_count": 2,
        },
        {
            "name": "Build retailer scrape health report",
            "command": [sys.executable, "-u", "scrapers/products/build_retailer_quality_report.py"],
        },
        {
            "name": "Build inventory quality report",
            "command": [sys.executable, "-u", "scrapers/products/inventory_quality_report.py"],
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
        "duration_seconds": int((completed_at - started_at).total_seconds()),
        "active_scrape_targets": active_target_count(),
        "steps": results,
    }

    JOB_REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
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