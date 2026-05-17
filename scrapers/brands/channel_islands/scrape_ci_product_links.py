import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("scrapers/brands/channel_islands/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://shop-au.cisurfboards.com"

TARGET_COLLECTIONS = [
    "/collections/board-models",
    "/collections/ect",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)"
}

INVALID_SLUG_PATTERNS = [
    "#",
    "comments",
    "videos",
    "attributes",
]

VALID_SLUG_REGEX = re.compile(r"^[a-z0-9\-]+$")


def is_valid_slug(slug: str) -> bool:
    slug = slug.strip().lower()

    if not slug:
        return False

    if slug.isdigit():
        return False

    if not VALID_SLUG_REGEX.match(slug):
        return False

    for pattern in INVALID_SLUG_PATTERNS:
        if pattern in slug:
            return False

    return True


def scrape_collection(collection_path: str) -> list:
    url = f"{BASE_URL}{collection_path}"

    print(f"Scraping {url}")

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    products = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/products/" not in href:
            continue

        clean_href = href.split("?")[0]
        clean_href = clean_href.split("#")[0]

        if clean_href.startswith("/"):
            clean_href = BASE_URL + clean_href

        slug = clean_href.rstrip("/").split("/")[-1].lower()

        if not is_valid_slug(slug):
            continue

        title = link.get_text(" ", strip=True)

        products[slug] = {
            "slug": slug,
            "product_url": clean_href,
            "title_hint": title,
            "source_collection": collection_path,
        }

    return list(products.values())


def main():
    all_products = {}

    for collection in TARGET_COLLECTIONS:
        try:
            results = scrape_collection(collection)

            for item in results:
                all_products[item["slug"]] = item

        except Exception as exc:
            print(f"FAILED {collection}: {exc}")

    final_products = sorted(
        all_products.values(),
        key=lambda x: x["slug"]
    )

    output_path = OUTPUT_DIR / "ci_product_links.json"

    output_path.write_text(
        json.dumps(final_products, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("")
    print(f"Saved {len(final_products)} clean products")
    print(output_path)


if __name__ == "__main__":
    main()