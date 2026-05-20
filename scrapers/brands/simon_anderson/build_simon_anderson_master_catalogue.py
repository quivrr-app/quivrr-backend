import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BRAND_NAME = "Simon Anderson"
BASE_URL = "https://simonandersonsurfboards.com"
SEED_URLS = [
    "https://simonandersonsurfboards.com/surfboards/",
    "https://simonandersonsurfboards.com/surfboards/custom-only-boards/",
]
OUTPUT_FILE = Path("scrapers/brands/simon_anderson/output/simon_anderson_master_catalogue_clean.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SIZE_RE = re.compile(
    r"(?:[A-Z0-9\-]+\s+)?"
    r"(?P<length>[4-9][’']\s*\d{1,2})\s+"
    r"(?:[A-Z][A-Z0-9\-]+\s+)?"
    r"(?P<width>\d{1,2}(?:\s+\d{1,2}/\d{1,2})?)\s+"
    r"(?P<thickness>\d(?:\s+\d{1,2}/\d{1,2})?)\s+"
    r"(?P<volume>\d{2}(?:\.\d+)?)\s*L?",
    re.IGNORECASE,
)


def clean(value):
    value = str(value or "")
    value = value.replace("’", "'").replace("‘", "'")
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def get_html(url):
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return response.text


def page_text(html):
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return clean(soup.get_text(" ", strip=True)) or ""


def discover_urls():
    urls = set()

    for seed in SEED_URLS:
        try:
            html = get_html(seed)
        except Exception:
            continue

        soup = BeautifulSoup(html, "html.parser")

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].split("?")[0].strip()
            url = urljoin(BASE_URL, href)
            parsed = urlparse(url)

            if parsed.netloc != "simonandersonsurfboards.com":
                continue

            if not parsed.path.startswith("/surfboards/"):
                continue

            slug = parsed.path.rstrip("/").split("/")[-1]

            if not slug or slug in {"surfboards", "custom-only-boards"}:
                continue

            urls.add(url)

    return sorted(urls)


def extract_title(soup, fallback_url):
    heading = soup.find("h1")

    if heading:
        title = clean(heading.get_text(" ", strip=True))
        if title:
            return title

    meta = soup.find("meta", property="og:title")

    if meta and meta.get("content"):
        title = clean(meta["content"])
        if title:
            title = title.replace("| Simon Anderson Surfboards", "").strip()
            return title

    slug = fallback_url.rstrip("/").split("/")[-1]
    return clean(slug.replace("-", " ").title())


def extract_image(soup):
    meta = soup.find("meta", property="og:image")

    if meta and meta.get("content"):
        return clean(meta["content"])

    image = soup.find("img")

    if image and image.get("src"):
        return urljoin(BASE_URL, image["src"])

    return None


def parse_sizes(text):
    rows = []

    for match in SIZE_RE.finditer(text):
        try:
            volume = float(match.group("volume"))
        except Exception:
            continue

        rows.append({
            "length": clean(match.group("length").replace(" ", "")),
            "width": clean(match.group("width")),
            "thickness": clean(match.group("thickness")),
            "volume_litres": volume,
        })

    deduped = []
    seen = set()

    for row in rows:
        key = (
            row["length"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    return deduped


def main():
    print("")
    print("Building Simon Anderson manufacturer catalogue")

    product_urls = discover_urls()
    print(f"Candidate product URLs discovered: {len(product_urls)}")

    rows = []
    seen = set()

    for url in product_urls:
        try:
            html = get_html(url)
        except Exception as exc:
            print(f"Skipped {url}: {exc}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        text = page_text(html)
        sizes = parse_sizes(text)

        if not sizes:
            print(f"No size rows: {url}")
            continue

        model = extract_title(soup, url)
        image = extract_image(soup)

        print(f"{model}: {len(sizes)} stock sizes")

        for size in sizes:
            key = (
                model,
                size["length"],
                size["width"],
                size["thickness"],
                size["volume_litres"],
            )

            if key in seen:
                continue

            seen.add(key)

            rows.append({
                "brand": BRAND_NAME,
                "model": model,
                "model_family": model,
                "board_category": "Surfboard",
                "length": size["length"],
                "width": size["width"],
                "thickness": size["thickness"],
                "volume_litres": size["volume_litres"],
                "construction": "PU",
                "fin_system": None,
                "tail_shape": None,
                "official_product_url": url,
                "official_image_url": image,
                "source": url,
                "source_product_title": model,
                "source_product_id": None,
                "source_variant_id": None,
                "source_variant_title": None,
                "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
            })

        time.sleep(0.25)

    if not rows:
        raise RuntimeError("No Simon Anderson catalogue rows were built")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print("")
    print("Simon Anderson catalogue build complete")
    print(f"Models: {len(set(r['model'] for r in rows))}")
    print(f"Rows: {len(rows)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Simon Anderson catalogue build failed: {exc}")
        sys.exit(1)
