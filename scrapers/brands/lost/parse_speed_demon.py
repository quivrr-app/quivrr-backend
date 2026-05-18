import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


URL = "https://lostsurfboards.net/surfboards/speed-demon/"
OUTPUT_FILE = Path("scrapers/brands/lost/output/speed_demon_parsed.json")

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
images = []
dimensions = []

h1 = soup.find("h1")
if h1:
    title = clean(h1.get_text(" ", strip=True))

meta_desc = soup.find("meta", attrs={"name": "description"})
if meta_desc:
    description = clean(meta_desc.get("content"))

for img in soup.find_all("img"):
    src = img.get("src") or img.get("data-src")

    if not src:
        continue

    if any(x in src.lower() for x in [
        "logo",
        "icon",
        "banner",
        "placeholder",
    ]):
        continue

    images.append(src)

images = sorted(set(images))

page_text = clean(soup.get_text(" ", strip=True))

dimension_pattern = re.compile(
    r"(\d+'?\d+)\s+x\s+([\d/\.]+)\s+x\s+([\d/\.]+)\s+x\s+([\d\.]+)\s*l",
    re.I,
)

for match in dimension_pattern.finditer(page_text):
    dimensions.append({
        "length": match.group(1),
        "width": match.group(2),
        "thickness": match.group(3),
        "volume_litres": match.group(4),
    })

dimensions = [dict(t) for t in {tuple(d.items()) for d in dimensions}]

result = {
    "url": URL,
    "title": title,
    "description": description,
    "image_count": len(images),
    "images": images[:20],
    "dimension_count": len(dimensions),
    "dimensions": dimensions,
}

OUTPUT_FILE.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("=" * 80)
print("LOST SPEED DEMON PARSE")
print("=" * 80)

print("")
print("TITLE:")
print(title)

print("")
print("DESCRIPTION:")
print(description[:1000] if description else None)

print("")
print("IMAGES:", len(images))
for img in images[:10]:
    print(img)

print("")
print("DIMENSIONS:", len(dimensions))
for row in dimensions[:30]:
    print(row)

print("")
print("Saved:", OUTPUT_FILE)
