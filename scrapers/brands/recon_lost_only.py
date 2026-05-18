import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


OUTPUT_FILE = Path("scrapers/brands/output/lost_only_recon_report.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

BASES = [
    "https://lostsurfboards.net",
    "https://lostsurfboards.com",
    "https://www.lostsurfboards.com",
]

PATHS = [
    "/",
    "/surfboards",
    "/board-models",
    "/models",
    "/collections/boards",
    "/collections/all",
    "/sitemap.xml",
    "/wp-sitemap.xml",
    "/wp-json/wp/v2/pages?per_page=100",
    "/wp-json/wp/v2/posts?per_page=100",
    "/wp-json/wp/v2/product?per_page=100",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
}


def fetch(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=(5, 10),
            allow_redirects=True,
        )

        content_type = response.headers.get("content-type", "")
        text = response.text[:300000]

        links = []
        possible_board_links = []

        if "html" in content_type or "<html" in text.lower():
            soup = BeautifulSoup(text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link["href"].split("?")[0].strip()
                full = urljoin(response.url, href)

                links.append(full)

                lowered = full.lower()
                if any(word in lowered for word in [
                    "surfboard",
                    "board",
                    "model",
                    "mayhem",
                    "driver",
                    "sub-driver",
                    "rocket",
                    "fish",
                    "puddle",
                    "quiver",
                ]):
                    possible_board_links.append(full)

        return {
            "url": url,
            "status_code": response.status_code,
            "final_url": response.url,
            "content_type": content_type,
            "length": len(response.text),
            "server": response.headers.get("server"),
            "powered_by": response.headers.get("x-powered-by"),
            "looks_wordpress": "wp-content" in text.lower() or "wp-json" in text.lower(),
            "looks_shopify": "cdn.shopify.com" in text or "Shopify" in text,
            "links_count": len(set(links)),
            "possible_board_links_count": len(set(possible_board_links)),
            "possible_board_links": sorted(set(possible_board_links))[:100],
            "error": None,
        }

    except Exception as exc:
        return {
            "url": url,
            "status_code": None,
            "final_url": None,
            "content_type": None,
            "length": 0,
            "server": None,
            "powered_by": None,
            "looks_wordpress": False,
            "looks_shopify": False,
            "links_count": 0,
            "possible_board_links_count": 0,
            "possible_board_links": [],
            "error": str(exc),
        }


def main():
    results = []

    print("")
    print("=" * 80)
    print("LOST ONLY RECON")
    print("=" * 80)

    for base in BASES:
        for path in PATHS:
            url = base.rstrip("/") + path
            result = fetch(url)
            results.append(result)

            print(
                result["status_code"],
                result["url"],
                "final:",
                result["final_url"],
                "wp:",
                result["looks_wordpress"],
                "shopify:",
                result["looks_shopify"],
                "board_links:",
                result["possible_board_links_count"],
                "error:",
                result["error"],
            )

    OUTPUT_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("Recon complete")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
