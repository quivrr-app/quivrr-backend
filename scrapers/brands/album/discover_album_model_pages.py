import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://albumsurf.com"
URL = "https://albumsurf.com/pages/board-models"

OUTPUT_FILE = Path("scrapers/brands/album/output/album_model_links.json")

KNOWN_MODELS = [
    "Sunstone",
    "Lightbender",
    "Veebee",
    "Twinsman",
    "Plasmic",
    "Vesper",
    "Delma",
    "Moonstone",
    "Townsend",
    "The End",
    "Darkness",
    "Whale Shark",
    "Insanity",
    "Warp Twin",
    "Freewing",
    "VB Secret Menu",
    "ProtoAtypical",
    "Bom Dia",
    "Disorder",
    "D'Boa",
]

headers = {
    "User-Agent": "Mozilla/5.0",
}

response = requests.get(URL, headers=headers, timeout=(10, 30))
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

links = []

for a in soup.find_all("a", href=True):
    href = a.get("href")
    text = a.get_text(" ", strip=True)
    full_url = urljoin(BASE_URL, href)

    lower_url = full_url.lower()

    if "albumsurf.com" not in full_url:
        continue

    if any(model.lower().replace("'", "").replace(" ", "-") in lower_url for model in KNOWN_MODELS):
        links.append({
            "name": text,
            "url": full_url,
        })
        continue

    if "/collections/" in lower_url and any(term in lower_url for term in ["concept", "board", "surf"]):
        links.append({
            "name": text,
            "url": full_url,
        })

seen = set()
deduped = []

for link in links:
    key = link["url"]

    if key in seen:
        continue

    seen.add(key)

    name = link["name"]

    if not name:
        slug = key.rstrip("/").split("/")[-1]
        name = slug.replace("-concept", "").replace("-", " ").title()

    deduped.append({
        "name": name,
        "url": key,
    })

deduped.sort(key=lambda row: row["name"].lower())

print("")
print("=" * 100)
print("ALBUM MODEL LINKS")
print("=" * 100)
print("Models:", len(deduped))

for link in deduped:
    print(link["name"], "=>", link["url"])

OUTPUT_FILE.write_text(
    json.dumps(deduped, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
