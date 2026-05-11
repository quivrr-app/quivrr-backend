import json
import re
from pathlib import Path

import requests

BASE_DIR = Path("scrapers/retailers/stockists")
SOURCE_FILE = BASE_DIR / "brand_stockist_sources.json"
RAW_DIR = BASE_DIR / "raw"
LOG_FILE = BASE_DIR / "logs" / "download_stockist_sources.log"

RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def safe_filename(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")

def main():
    with SOURCE_FILE.open("r", encoding="utf-8") as f:
        sources = json.load(f)

    log_lines = []

    for source in sources:
        brand = source["brand"]
        url = source["stockist_url"]
        filename = RAW_DIR / f"{safe_filename(brand)}.html"

        print(f"Downloading {brand}: {url}")

        try:
            response = requests.get(
                url,
                timeout=25,
                headers={
                    "User-Agent": "Mozilla/5.0 QuivrrBot/0.1"
                }
            )

            filename.write_text(response.text, encoding="utf-8", errors="ignore")

            log_lines.append(
                f"{brand} | {response.status_code} | {len(response.text)} bytes | {url}"
            )

            print(f"  OK {response.status_code} | {len(response.text)} bytes")

        except Exception as exc:
            log_lines.append(f"{brand} | ERROR | {exc} | {url}")
            print(f"  ERROR {exc}")

    LOG_FILE.write_text("\n".join(log_lines), encoding="utf-8")

    print("")
    print("Download complete")
    print(f"Raw files: {RAW_DIR}")
    print(f"Log file: {LOG_FILE}")

if __name__ == "__main__":
    main()
