import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.chillisurfboards.com"

TEST_URLS = [
    "https://www.chillisurfboards.com/surfboards/detail.php?id=25279&direct=1&region=aus",
    "https://www.chillisurfboards.com/surfboards/detail.php?id=515&direct=1&region=aus",
    "https://www.chillisurfboards.com/surfboards/detail.php?id=7234&direct=1&region=aus",
]

OUTPUT_FILE = Path("scrapers/brands/chilli/output/chilli_detail_probe.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}

session = requests.Session()
session.headers.update(HEADERS)

session.get(
    f"{BASE_URL}/changeregion.php?region=aus",
    timeout=(10, 30),
)

results = []

print("")
print("=" * 100)
print("CHILLI DETAIL PAGE PROBE")
print("=" * 100)

for url in TEST_URLS:

    row = {
        "url": url,
        "title": None,
        "matches": [],
    }

    try:
        response = session.get(
            url,
            timeout=(10, 30),
        )

        soup = BeautifulSoup(response.text, "html.parser")

        row["title"] = soup.title.get_text(" ", strip=True) if soup.title else None

        html = response.text
        html = html.replace("×", "x")

        pattern = (
            r"\d+'\s*\d{1,2}\"?\s*x\s*"
            r"\d+(?:\.\d+)?\s*x\s*"
            r"\d+(?:\.\d+)?\s*x?\s*"
            r"\d+(?:\.\d+)?\s*L"
        )

        matches = re.findall(
            pattern,
            html,
            flags=re.IGNORECASE,
        )

        unique = []

        for match in matches:
            value = " ".join(match.split())

            if value not in unique:
                unique.append(value)

        row["matches"] = unique

        print("")
        print("-" * 100)
        print("URL:", url)
        print("Title:", row["title"])
        print("Matches:", len(unique))

        for item in unique[:30]:
            print(" -", item)

    except Exception as exc:

        row["error"] = str(exc)

        print("")
        print("ERROR:", exc)

    results.append(row)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
