import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import requests


OUTPUT_DIR = Path("scrapers/brands/channel_islands/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SITEMAPS = [
    "https://shop-au.cisurfboards.com/sitemap.xml",
    "https://shop-au.cisurfboards.com/sitemap_products_1.xml",
    "https://cisurfboards.com/sitemap.xml",
    "https://cisurfboards.com/sitemap_products_1.xml",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)"
}

EXCLUDE_TERMS = [
    "gift",
    "accessory",
    "accessories",
    "fin",
    "traction",
    "leash",
    "cover",
    "shirt",
    "tee",
    "hat",
    "grip",
    "wax",
    "sticker",
    "towel",
    "custom-board-tracker",
]

def normalise_slug(url: str) -> str:
    clean = url.split("?")[0].split("#")[0].rstrip("/")
    return clean.split("/")[-1].lower()

def looks_like_product(url: str) -> bool:
    if "/products/" not in url:
        return False

    slug = normalise_slug(url)

    if not slug or slug.isdigit():
        return False

    for term in EXCLUDE_TERMS:
        if term in slug:
            return False

    return True

def fetch_xml(url: str) -> str:
    print(f"Checking {url}")
    response = requests.get(url, headers=HEADERS, timeout=30)
    print(f"Status {response.status_code}")
    response.raise_for_status()
    return response.text

def extract_urls_from_xml(xml_text: str) -> list[str]:
    urls = []

    root = ET.fromstring(xml_text)

    for elem in root.iter():
        if elem.tag.endswith("loc") and elem.text:
            urls.append(elem.text.strip())

    return urls

def main() -> None:
    discovered = {}

    for sitemap in SITEMAPS:
        try:
            xml_text = fetch_xml(sitemap)
            urls = extract_urls_from_xml(xml_text)

            for url in urls:
                if url.endswith(".xml"):
                    try:
                        child_xml = fetch_xml(url)
                        child_urls = extract_urls_from_xml(child_xml)
                    except Exception:
                        child_urls = []

                    for child_url in child_urls:
                        if looks_like_product(child_url):
                            slug = normalise_slug(child_url)
                            discovered[slug] = {
                                "slug": slug,
                                "product_url": child_url.split("?")[0].split("#")[0],
                                "source": url,
                            }

                elif looks_like_product(url):
                    slug = normalise_slug(url)
                    discovered[slug] = {
                        "slug": slug,
                        "product_url": url.split("?")[0].split("#")[0],
                        "source": sitemap,
                    }

        except Exception as exc:
            print(f"FAILED {sitemap}: {exc}")

    products = sorted(discovered.values(), key=lambda item: item["slug"])

    output_path = OUTPUT_DIR / "ci_sitemap_product_links.json"
    output_path.write_text(
        json.dumps(products, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("")
    print(f"Saved {len(products)} sitemap product links")
    print(output_path)

    print("")
    print("First 20:")
    for item in products[:20]:
        print(f"{item['slug']} | {item['product_url']}")

if __name__ == "__main__":
    main()
