import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("scrapers/retailers/recon_focused")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {
        "name": "Boardcave",
        "url": "https://www.boardcave.com.au",
    },
    {
        "name": "Coopers Surf",
        "url": "https://cooperssurf.com.au",
    },
    {
        "name": "Coopers Board Store",
        "url": "https://coopersboardstore.com.au",
    },
]

PATHS = [
    "/",
    "/robots.txt",
    "/sitemap.xml",
    "/collections/surfboards",
    "/products.json?limit=250",
    "/graphql",
    "/search?q=surfboard",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
}


def detect_platform(text, headers):
    combined = (
        (text or "") +
        " " +
        " ".join(f"{k}:{v}" for k, v in headers.items())
    ).lower()

    hits = []

    checks = {
        "magento": [
            "magento",
            "mage-cache",
            "catalogsearch",
        ],
        "shopify": [
            "shopify",
            "cdn.shopify.com",
            "products.json",
        ],
        "woocommerce": [
            "woocommerce",
            "wp-content",
            "wp-json",
        ],
        "cloudflare": [
            "cloudflare",
            "cf-ray",
            "__cf_bm",
        ],
    }

    for platform, patterns in checks.items():
        if any(pattern in combined for pattern in patterns):
            hits.append(platform)

    return hits


async def fetch(client, target, path):
    url = urljoin(target["url"], path)

    try:
        response = await client.get(url, follow_redirects=True)

        text = response.text or ""

        soup = BeautifulSoup(text, "html.parser")

        title = soup.title.get_text(strip=True) if soup.title else ""

        result = {
            "target": target["name"],
            "path": path,
            "url": str(response.url),
            "status": response.status_code,
            "title": title,
            "platforms": detect_platform(text, response.headers),
        }

        print(
            f"{target['name']:22} "
            f"{path:35} "
            f"{response.status_code:<4} "
            f"{','.join(result['platforms']) or 'unknown'}"
        )

        return result

    except Exception as exc:
        print(f"{target['name']:22} {path:35} ERROR {exc}")

        return {
            "target": target["name"],
            "path": path,
            "error": str(exc),
        }


async def main():
    results = []

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=30,
    ) as client:

        for target in TARGETS:

            print("")
            print("=" * 80)
            print(target["name"])
            print("=" * 80)

            for path in PATHS:
                result = await fetch(client, target, path)
                results.append(result)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    output_file = OUTPUT_DIR / f"focused_recon_{timestamp}.json"

    output_file.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8"
    )

    print("")
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
