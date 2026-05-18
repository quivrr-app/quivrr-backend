import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


URL = "https://lostsurfboards.net/surfboards/speed-demon/"
OUTPUT_FILE = Path("scrapers/brands/lost/output/speed_demon_clean_parse.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


response = requests.get(URL, headers=HEADERS, timeout=(10, 30))
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

title = None
description = None
hero_image = None
dimensions = []

h1 = soup.find("h1")

if h1:
    title = clean(h1.get_text(" ", strip=True))

og_desc = soup.find("meta", attrs={"property": "og:description"})

if og_desc:
    description = clean(og_desc.get("content"))

og_image = soup.find("meta", attrs={"property": "og:image"})

if og_image:
    hero_image = og_image.get("content")

page_text = clean(soup.get_text(" ", strip=True))

dimension_pattern = re.compile(
    r"(\d+[’']\d+)\s*</td>\s*<td[^>]*>\s*([\d\.]+)\s*</td>\s*<td[^>]*>\s*([\d\.]+)\s*</td>\s*<td[^>]*>\s*([\d\.]+)",
    re.I,
)

html = str(soup)

for match in dimension_pattern.finditer(html):
    dimensions.append({
        "length": match.group(1).replace("’", "'"),
        "width": match.group(2),
        "thickness": match.group(3),
        "volume_litres": match.group(4),
    })

unique = []
seen = set()

for row in dimensions:
    key = tuple(row.items())

    if key in seen:
        continue

    seen.add(key)
    unique.append(row)

dimensions = unique

result = {
    "url": URL,
    "title": title,
    "description": description,
    "hero_image": hero_image,
    "dimension_count": len(dimensions),
    "dimensions": dimensions,
}

OUTPUT_FILE.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("=" * 80)
print("LOST CLEAN PARSE")
print("=" * 80)

print("")
print("TITLE:")
print(title)

print("")
print("DESCRIPTION:")
print(description[:800] if description else None)

print("")
print("HERO IMAGE:")
print(hero_image)

print("")
print("DIMENSIONS:", len(dimensions))

for row in dimensions:
    print(row)

print("")
print("Saved:", OUTPUT_FILE)
