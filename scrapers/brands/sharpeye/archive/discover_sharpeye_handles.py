import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://sharpeyesurfboards.com"

OUTPUT_FILE = Path("scrapers/brands/sharpeye/output/sharpeye_handle_discovery.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


candidate_pages = [
    BASE_URL,
    f"{BASE_URL}/pages/surfboards",
    f"{BASE_URL}/pages/boards",
    f"{BASE_URL}/collections",
    f"{BASE_URL}/sitemap.xml",
]

handles = set()
results = []

print("")
print("=" * 100)
print("SHARP EYE HANDLE DISCOVERY")
print("=" * 100)

for url in candidate_pages:
    row = {
        "url": url,
        "status_code": None,
        "title": None,
        "collection_links": [],
        "product_links": [],
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        row["status_code"] = response.status_code

        print("")
        print("URL:", url)
        print("Status:", response.status_code)

        soup = BeautifulSoup(response.text, "html.parser")
        row["title"] = soup.title.get_text(" ", strip=True) if soup.title else None

        hrefs = []

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            hrefs.append(href)

        for href in hrefs:
            if "/collections/" in href:
                full = urljoin(BASE_URL, href)
                row["collection_links"].append(full)

                match = re.search(r"/collections/([^/?#]+)", full)

                if match:
                    handles.add(match.group(1))

            if "/products/" in href:
                row["product_links"].append(urljoin(BASE_URL, href))

        print("Title:", row["title"])
        print("Collection links:", len(row["collection_links"]))
        print("Product links:", len(row["product_links"]))

    except Exception as exc:
        row["error"] = str(exc)
        print("ERROR:", exc)

    results.append(row)

print("")
print("=" * 100)
print("DISCOVERED COLLECTION HANDLES")
print("=" * 100)

for handle in sorted(handles):
    print(handle)

OUTPUT_FILE.write_text(
    json.dumps(
        {
            "handles": sorted(handles),
            "results": results,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
