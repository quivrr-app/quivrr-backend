import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://christensonsurfboards.com"

CATEGORY_URLS = [
    "https://christensonsurfboards.com/fish",
    "https://christensonsurfboards.com/performance",
    "https://christensonsurfboards.com/alternative-short",
    "https://christensonsurfboards.com/alternative-mids",
    "https://christensonsurfboards.com/longboards",
    "https://christensonsurfboards.com/stepups-guns",
]

OUTPUT_FILE = Path(
    "scrapers/brands/christenson/output/christenson_model_links.json"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


results = []
seen = set()


print("")
print("=" * 100)
print("DISCOVER CHRISTENSON MODEL LINKS")
print("=" * 100)

for category_url in CATEGORY_URLS:

    print("")
    print("CATEGORY:", category_url)

    response = requests.get(
        category_url,
        headers=HEADERS,
        timeout=(10, 30),
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for a in soup.find_all("a", href=True):

        href = a.get("href")

        if not href:
            continue

        full_url = urljoin(BASE_URL, href)

        if full_url in seen:
            continue

        if full_url.rstrip("/") == category_url.rstrip("/"):
            continue

        if not full_url.startswith(BASE_URL):
            continue

        slug = full_url.rstrip("/").split("/")[-1]

        if len(slug) < 3:
            continue

        blacklist = [
            "about",
            "team",
            "news",
            "shipping",
            "where-to-buy",
            "store",
            "custom",
        ]

        if slug.lower() in blacklist:
            continue

        seen.add(full_url)

        name = slug.replace("-", " ").title()

        results.append({
            "name": name,
            "url": full_url,
            "category": category_url.split("/")[-1],
        })

        print(name, "=>", full_url)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("=" * 100)
print("SUMMARY")
print("=" * 100)
print("Model pages:", len(results))
print("Saved:", OUTPUT_FILE)
