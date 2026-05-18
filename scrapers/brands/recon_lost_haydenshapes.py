import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT_FILE = Path("scrapers/brands/output/lost_haydenshapes_recon_report.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

BRANDS = {
    "lost": [
        "https://lostsurfboards.net",
        "https://www.lostsurfboards.net",
        "https://lostsurfboards.com",
        "https://www.lostsurfboards.com",
    ],
    "haydenshapes": [
        "https://haydenshapes.com",
        "https://www.haydenshapes.com",
        "https://haydenshapes.com.au",
        "https://www.haydenshapes.com.au",
    ],
}

PATHS = [
    "/",
    "/collections/all",
    "/collections/surfboards",
    "/collections/boards",
    "/collections/shortboards",
    "/products.json?limit=250",
    "/sitemap.xml",
    "/sitemap_products_1.xml",
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
            timeout=25,
            allow_redirects=True,
        )

        content_type = response.headers.get("content-type", "")
        text = response.text[:200000]

        product_links = []
        collection_links = []

        if "html" in content_type or "<html" in text.lower():
            soup = BeautifulSoup(text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link["href"].split("?")[0].strip()

                if "/products/" in href:
                    product_links.append(href)

                if "/collections/" in href:
                    collection_links.append(href)

        return {
            "url": url,
            "status_code": response.status_code,
            "final_url": response.url,
            "content_type": content_type,
            "length": len(response.text),
            "looks_shopify": (
                "cdn.shopify.com" in text
                or "Shopify" in text
                or "/products.json" in text
            ),
            "has_products_json": (
                "products" in text[:1000].lower()
                and "application/json" in content_type.lower()
            ),
            "product_links_found": sorted(set(product_links))[:60],
            "product_links_count": len(set(product_links)),
            "collection_links_found": sorted(set(collection_links))[:60],
            "collection_links_count": len(set(collection_links)),
            "error": None,
        }

    except Exception as exc:
        return {
            "url": url,
            "status_code": None,
            "final_url": None,
            "content_type": None,
            "length": 0,
            "looks_shopify": False,
            "has_products_json": False,
            "product_links_found": [],
            "product_links_count": 0,
            "collection_links_found": [],
            "collection_links_count": 0,
            "error": str(exc),
        }


def main():
    report = {}

    for brand, bases in BRANDS.items():
        print("")
        print("=" * 80)
        print(brand.upper())
        print("=" * 80)

        report[brand] = []

        for base in bases:
            for path in PATHS:
                url = base.rstrip("/") + path
                result = fetch(url)
                report[brand].append(result)

                print(
                    result["status_code"],
                    result["url"],
                    "products:",
                    result["product_links_count"],
                    "collections:",
                    result["collection_links_count"],
                    "shopify:",
                    result["looks_shopify"],
                    "error:",
                    result["error"],
                )

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("Recon complete")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
