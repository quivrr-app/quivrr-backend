import json
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("scrapers/brands/channel_islands/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "ci_canonical_model_links.json"

TARGETS = [
    {
        "region": "global",
        "source": "board-models",
        "url": "https://cisurfboards.com/collections/board-models",
    },
    {
        "region": "global",
        "source": "shortboards",
        "url": "https://cisurfboards.com/collections/shortboards",
    },
    {
        "region": "au",
        "source": "board-models",
        "url": "https://shop-au.cisurfboards.com/collections/board-models",
    },
    {
        "region": "au",
        "source": "board-models-shortboard",
        "url": "https://shop-au.cisurfboards.com/collections/board-models/shortboard",
    },
]

SITEMAPS = [
    {
        "region": "global",
        "source": "sitemap",
        "url": "https://cisurfboards.com/sitemap.xml",
    },
    {
        "region": "au",
        "source": "sitemap",
        "url": "https://shop-au.cisurfboards.com/sitemap.xml",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)"
}

INVALID_SLUG_PARTS = [
    "#",
    "gift-card",
    "e-gift",
    "accessories",
    "wetsuit",
    "better-everyday",
    "happy-everyday",
    "g-skate",
    "twin-pin",
]

INVALID_TITLE_VALUES = {
    "attributes",
    "comments",
    "videos",
    "view",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    return " ".join(value.split()).strip()


def looks_like_model_title(value: str) -> bool:
    title = clean_text(value)

    if not title:
        return False

    lowered = title.lower()

    if lowered in INVALID_TITLE_VALUES:
        return False

    if "{%" in title or "{{" in title or "}}" in title:
        return False

    return True


def looks_like_model_slug(slug: str) -> bool:
    cleaned_slug = clean_text(slug)

    if not cleaned_slug:
        return False

    if "{" in cleaned_slug or "}" in cleaned_slug or "%" in cleaned_slug:
        return False

    return True


def model_name_from_slug(slug: str) -> str:
    parts = [part for part in clean_text(slug).split("-") if part]
    return " ".join(
        part.upper() if len(part) <= 2 else part.title()
        for part in parts
    )


def extract_urls_from_xml(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    urls = []

    for element in root.iter():
        if element.tag.endswith("loc") and element.text:
            urls.append(element.text.strip())

    return urls


def fetch_xml(url: str) -> str:
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def fetch_models(target: dict) -> list[dict]:
    print(f"Scraping {target['url']}")

    response = requests.get(
        target["url"],
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/products/" not in href:
            continue

        href = href.split("?")[0].split("#")[0]

        slug = href.rstrip("/").split("/")[-1].lower()

        if not slug:
            continue

        if not looks_like_model_slug(slug):
            continue

        if any(part in slug for part in INVALID_SLUG_PARTS):
            continue

        title = clean_text(link.get_text(" ", strip=True))

        if not looks_like_model_title(title):
            continue

        if href.startswith("/"):
            base = "https://cisurfboards.com" if target["region"] == "global" else "https://shop-au.cisurfboards.com"
            href = base + href

        results[slug] = {
            "slug": slug,
            "model_name": title,
            "product_url": href,
            "region": target["region"],
            "source": target["source"],
        }

    return list(results.values())


def fetch_sitemap_models(target: dict) -> list[dict]:
    print(f"Scraping {target['url']}")

    discovered = {}
    queue = [target["url"]]
    visited = set()

    while queue:
        sitemap_url = queue.pop(0)

        if sitemap_url in visited:
            continue

        visited.add(sitemap_url)

        try:
            xml_text = fetch_xml(sitemap_url)
        except Exception as exc:
            print(f"FAILED {sitemap_url}: {exc}")
            continue

        for url in extract_urls_from_xml(xml_text):
            if url.endswith(".xml"):
                queue.append(url)
                continue

            if "/products/" not in url:
                continue

            href = url.split("?")[0].split("#")[0]
            slug = href.rstrip("/").split("/")[-1].lower()

            if not looks_like_model_slug(slug):
                continue

            if any(part in slug for part in INVALID_SLUG_PARTS):
                continue

            discovered[slug] = {
                "slug": slug,
                "model_name": model_name_from_slug(slug),
                "product_url": href,
                "region": target["region"],
                "source": target["source"],
            }

    return list(discovered.values())


def merge_model(merged: dict, item: dict) -> None:
    slug = item["slug"]

    if slug not in merged:
        merged[slug] = item
        return

    existing = merged[slug]

    # Prefer human-readable collection titles over sitemap-derived slug names.
    if existing.get("source") == "sitemap" and item.get("source") != "sitemap":
        merged[slug] = item
        return

    # Prefer the official global canonical source when both are available.
    if existing.get("region") != "global" and item.get("region") == "global":
        merged[slug] = item


def main() -> None:
    merged = {}

    for target in TARGETS:
        try:
            for item in fetch_models(target):
                merge_model(merged, item)
        except Exception as exc:
            print(f"FAILED {target['url']}: {exc}")

    for target in SITEMAPS:
        for item in fetch_sitemap_models(target):
            merge_model(merged, item)

    final = sorted(
        merged.values(),
        key=lambda x: x["model_name"].lower()
    )

    OUTPUT_FILE.write_text(
        json.dumps(final, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print(f"Saved {len(final)} canonical CI models")
    print(OUTPUT_FILE)

    print("")
    print("Models:")
    for item in final:
        print(f"{item['model_name']} | {item['slug']} | {item['region']} | {item['source']}")


if __name__ == "__main__":
    main()
