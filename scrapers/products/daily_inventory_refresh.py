import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("scrapers/products/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / f"daily_inventory_refresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

STEPS = [
    "scrapers/products/shopify_scraper.py",
    "scrapers/products/woocommerce_scraper.py",
    "scrapers/products/filter_surfboards.py",
    "scrapers/products/normalise_surfboards.py",
    "scrapers/products/build_grouped_inventory_index.py",
    "scrapers/products/inventory_quality_report.py"
]

def write_log(message):
    print(message)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(message + "\n")

def run_step(step):
    write_log("")
    write_log(f"Running {step}")

    process = subprocess.Popen(
        [sys.executable, step],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    for line in process.stdout:
        write_log(line.rstrip())

    process.wait()

    if process.returncode != 0:
        raise SystemExit(f"Failed: {step}")

def main():
    write_log("Quivrr daily inventory refresh started")
    write_log(datetime.now().isoformat())

    for step in STEPS:
        run_step(step)

    write_log("")
    write_log("Quivrr daily inventory refresh complete")
    write_log(datetime.now().isoformat())
    write_log(f"Log saved: {LOG_FILE}")

if __name__ == "__main__":
    main()
