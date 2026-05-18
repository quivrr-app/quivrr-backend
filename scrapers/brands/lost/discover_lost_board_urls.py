import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URLS = [
    "https://lostsurfboards.net/product-category/surfboards/",
    "https://lostsurfboards.net/boards/",
    "https://lostsurfboards.net/surfboards/",
]

OUTPUT_FILE = Path("scrapers/brands/lost/output/lost_board_urls.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}

SKIP_TERMS = [
    "/product-category/",
    "/category/",
    "/tag/",
    "/cart",
    "/checkout",
    "/account",
    "/technology",
    "/team",
    "/blog",
    "/video",
    "/videos",
    "/news",
    "/dealer",
    "/retailer",
    "/contact",
]


def get_links_from_page(url):
    response = requests.get(url, headers=HEADERS, timeout=(10, 30))
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links = set()

    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        full_url = urljoin(response.url, href).split("?")[0]

        lowered = full_url.lower()

        if "lostsurfboards.net/surfboards/" not in lowered:
            continue

        if lowered.rstrip("/") == "https://lostsurfboards.net/surfboards":
            continue

        if any(skip in lowered for skip in SKIP_TERMS):
            continue

        links.add(full_url.rstrip("/") + "/")

    return sorted(links)


def main():
    all_links = set()

    print("")
    print("=" * 80)
    print("LOST BOARD URL DISCOVERY")
    print("=" * 80)

    for url in BASE_URLS:
        try:
            links = get_links_from_page(url)
            print(url, "links:", len(links))
            all_links.update(links)
        except Exception as exc:
            print(url, "error:", exc)

    links = sorted(all_links)

    print("")
    print(f"Board URLs found: {len(links)}")
    print("")

    for url in links[:160]:
        print(url)

    OUTPUT_FILE.write_text(
        json.dumps(links, indent=2),
        encoding="utf-8",
    )

    print("")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
