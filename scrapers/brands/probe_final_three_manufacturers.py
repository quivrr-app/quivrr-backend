import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("scrapers/brands/_debug")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SITES = {
    "simon_anderson": "https://simonandersonsurfboards.com/surfboards/",
    "pukas": "https://pukassurf.com/surfboards/",
    "dark_arts": "https://darkartssurf.com/collections/surfboards",
}

SIZE_PATTERNS = [
    re.compile(r"[4-9]'\s*\d{1,2}.*?\d{2}(?:\.\d+)?\s*L", re.IGNORECASE),
    re.compile(r"[4-9]’\s*\d{1,2}.*?\d{2}(?:\.\d+)?\s*L", re.IGNORECASE),
    re.compile(r"\d{2}(?:\.\d+)?\s*lit", re.IGNORECASE),
]

def clean(value):
    value = str(value or "")
    value = value.replace("’", "'").replace("‘", "'")
    value = re.sub(r"\s+", " ", value).strip()
    return value

def fetch(url):
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return response.text

def extract_links(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].split("?")[0].strip()
        url = urljoin(base_url, href)
        parsed = urlparse(url)

        if parsed.netloc != urlparse(base_url).netloc:
            continue

        label = clean(anchor.get_text(" ", strip=True))

        links.append({
            "label": label,
            "url": url,
            "path": parsed.path,
        })

    unique = []
    seen = set()

    for link in links:
        if link["url"] in seen:
            continue

        seen.add(link["url"])
        unique.append(link)

    return unique

def analyse_page(name, base_url):
    print("")
    print("=" * 80)
    print(name)
    print(base_url)
    print("=" * 80)

    html = fetch(base_url)

    soup = BeautifulSoup(html, "html.parser")
    text = clean(soup.get_text(" ", strip=True))
    links = extract_links(base_url, html)

    (OUTPUT_DIR / f"{name}_landing.html").write_text(html, encoding="utf-8")
    (OUTPUT_DIR / f"{name}_landing_text.txt").write_text(text, encoding="utf-8")
    (OUTPUT_DIR / f"{name}_links.json").write_text(
        json.dumps(links, indent=2),
        encoding="utf-8"
    )

    print(f"Links found: {len(links)}")
    print(f"Landing text length: {len(text)}")

    possible = []

    for link in links:
        lower = (link["url"] + " " + link["label"]).lower()

        if any(token in lower for token in [
            "surfboard",
            "boards",
            "model",
            "collections",
            "product",
            "shop",
        ]):
            possible.append(link)

    print(f"Possible model/product links: {len(possible)}")

    for link in possible[:20]:
        print(f"- {link['label'][:60]} | {link['url']}")

    print("")
    print("Landing size pattern hits:")

    for pattern in SIZE_PATTERNS:
        hits = pattern.findall(text)

        print(f"{pattern.pattern}: {len(hits)}")

        for hit in hits[:5]:
            print(f"  {hit[:150]}")

    sample_results = []

    for link in possible[:12]:
        try:
            page_html = fetch(link["url"])
        except Exception as exc:
            sample_results.append({
                "url": link["url"],
                "label": link["label"],
                "error": str(exc),
            })
            continue

        page_soup = BeautifulSoup(page_html, "html.parser")
        page_text = clean(page_soup.get_text(" ", strip=True))

        hits = []

        for pattern in SIZE_PATTERNS:
            hits.extend(pattern.findall(page_text))

        sample_results.append({
            "url": link["url"],
            "label": link["label"],
            "text_length": len(page_text),
            "size_hit_count": len(hits),
            "sample_hits": hits[:10],
        })

    (OUTPUT_DIR / f"{name}_sample_model_probe.json").write_text(
        json.dumps(sample_results, indent=2),
        encoding="utf-8"
    )

    print("")
    print(f"Debug written under {OUTPUT_DIR}")

for name, url in SITES.items():
    try:
        analyse_page(name, url)
    except Exception as exc:
        print("")
        print(f"{name} failed: {exc}")
