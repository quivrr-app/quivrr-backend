import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.chillisurfboards.com"

URLS = [
    f"{BASE_URL}/regionselector.php",
    f"{BASE_URL}/au/",
    f"{BASE_URL}/australia/",
    f"{BASE_URL}/surfboards/",
    f"{BASE_URL}/au/surfboards/",
    f"{BASE_URL}/surfboards.php",
    f"{BASE_URL}/boards/",
    f"{BASE_URL}/models/",
    f"{BASE_URL}/sitemap.xml",
]

OUTPUT_FILE = Path("scrapers/brands/chilli/output/chilli_path_probe.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}

results = []
links_seen = set()

print("")
print("=" * 100)
print("CHILLI PATH PROBE")
print("=" * 100)

for url in URLS:
    row = {
        "url": url,
        "status_code": None,
        "final_url": None,
        "title": None,
        "links": [],
    }

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=(10, 30),
            allow_redirects=True,
        )

        soup = BeautifulSoup(response.text, "html.parser")

        row["status_code"] = response.status_code
        row["final_url"] = response.url
        row["title"] = soup.title.get_text(" ", strip=True) if soup.title else None

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            full = urljoin(BASE_URL, href)

            if "chillisurfboards.com" in full:
                links_seen.add(full)
                row["links"].append(full)

        print("")
        print("URL:", url)
        print("Final:", response.url)
        print("Status:", response.status_code)
        print("Title:", row["title"])
        print("Links:", len(row["links"]))

        for link in row["links"][:20]:
            print(" -", link)

    except Exception as exc:
        row["error"] = str(exc)

        print("")
        print("URL:", url)
        print("ERROR:", exc)

    results.append(row)

print("")
print("=" * 100)
print("INTERESTING LINKS")
print("=" * 100)

interesting = []

for link in sorted(links_seen):
    lower = link.lower()

    if any(term in lower for term in ["surfboard", "board", "model", "shortboard", "range", "collection"]):
        interesting.append(link)

for link in interesting[:100]:
    print(link)

OUTPUT_FILE.write_text(
    json.dumps(
        {
            "results": results,
            "interesting_links": interesting,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
