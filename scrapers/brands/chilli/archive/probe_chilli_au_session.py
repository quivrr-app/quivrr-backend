import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.chillisurfboards.com"

OUTPUT_FILE = Path("scrapers/brands/chilli/output/chilli_au_session_probe.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}

session = requests.Session()
session.headers.update(HEADERS)

print("")
print("=" * 100)
print("CHILLI AU SESSION PROBE")
print("=" * 100)

region_url = f"{BASE_URL}/changeregion.php?region=aus"

region_response = session.get(
    region_url,
    timeout=(10, 30),
    allow_redirects=True,
)

print("")
print("Region selector response")
print("Status:", region_response.status_code)
print("Final:", region_response.url)

print("")
print("Cookies")
print(session.cookies.get_dict())

TARGETS = [
    BASE_URL,
    f"{BASE_URL}/surfboards",
    f"{BASE_URL}/boards",
    f"{BASE_URL}/models",
]

results = []
all_links = set()

for url in TARGETS:

    row = {
        "url": url,
        "status": None,
        "final_url": None,
        "title": None,
        "links": [],
    }

    try:
        response = session.get(
            url,
            timeout=(10, 30),
            allow_redirects=True,
        )

        soup = BeautifulSoup(response.text, "html.parser")

        row["status"] = response.status_code
        row["final_url"] = response.url
        row["title"] = soup.title.get_text(" ", strip=True) if soup.title else None

        for link in soup.find_all("a", href=True):

            href = link.get("href")
            full = urljoin(BASE_URL, href)

            if "chillisurfboards.com" in full:
                all_links.add(full)
                row["links"].append(full)

        print("")
        print("-" * 100)
        print("URL:", url)
        print("Final:", response.url)
        print("Status:", response.status_code)
        print("Title:", row["title"])
        print("Links:", len(row["links"]))

        for link in row["links"][:30]:
            print(" -", link)

    except Exception as exc:

        row["error"] = str(exc)

        print("")
        print("ERROR:", exc)

    results.append(row)

interesting = []

for link in sorted(all_links):

    lower = link.lower()

    if any(term in lower for term in [
        "model",
        "board",
        "surfboard",
        "shortboard",
        "mid",
        "twin",
        "fish",
        "step",
    ]):
        interesting.append(link)

print("")
print("=" * 100)
print("INTERESTING LINKS")
print("=" * 100)

for link in interesting[:200]:
    print(link)

OUTPUT_FILE.write_text(
    json.dumps(
        {
            "cookies": session.cookies.get_dict(),
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
