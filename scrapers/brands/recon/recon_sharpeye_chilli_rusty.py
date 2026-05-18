import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BRANDS = {
    "SharpEye": [
        "https://www.sharpeyesurfboards.com",
    ],
    "Chilli": [
        "https://www.chillisurfboards.com",
    ],
    "Rusty": [
        "https://rustysurfboards.com",
    ],
}

PROBE_PATHS = [
    "",
    "/robots.txt",
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/products.json?limit=5",
    "/collections/all/products.json?limit=5",
    "/wp-json",
    "/wp-json/wp/v2",
    "/collections/all",
    "/surfboards",
    "/boards",
    "/products",
]

OUTPUT_FILE = Path("scrapers/brands/recon/sharpeye_chilli_rusty_recon.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


def detect_platform(text, headers):
    lowered = text.lower()

    if "cdn.shopify.com" in lowered or "shopify" in lowered:
        return "Shopify"

    if "woocommerce" in lowered:
        return "WooCommerce"

    if "wp-content" in lowered or "wp-json" in lowered:
        return "WordPress"

    if "bigcommerce" in lowered:
        return "BigCommerce"

    if "magento" in lowered:
        return "Magento"

    if "next.js" in lowered or "_next/" in lowered:
        return "NextJS"

    if "cloudflare" in lowered:
        return "Cloudflare Protected"

    server = headers.get("server", "").lower()

    if "cloudflare" in server:
        return "Cloudflare Edge"

    return "Unknown"


results = []

print("")
print("=" * 100)
print("SHARPEYE + CHILLI + RUSTY RECON")
print("=" * 100)

for brand, bases in BRANDS.items():

    print("")
    print("#" * 100)
    print(brand.upper())
    print("#" * 100)

    for base in bases:

        for probe in PROBE_PATHS:

            url = base.rstrip("/") + probe

            row = {
                "brand": brand,
                "base": base,
                "probe": probe,
                "url": url,
            }

            try:
                response = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=(10, 30),
                    allow_redirects=True,
                )

                text = response.text

                soup = BeautifulSoup(text, "html.parser")

                title = soup.title.get_text(" ", strip=True) if soup.title else None

                platform = detect_platform(text, response.headers)

                links = []

                for link in soup.find_all("a", href=True):
                    href = link["href"].strip()
                    full = urljoin(response.url, href).split("?")[0]

                    if any(word in full.lower() for word in [
                        "surfboard",
                        "board",
                        "model",
                        "product",
                        "collections",
                    ]):
                        links.append(full)

                links = sorted(set(links))

                row.update({
                    "status_code": response.status_code,
                    "final_url": response.url,
                    "title": title,
                    "platform": platform,
                    "content_length": len(text),
                    "content_type": response.headers.get("content-type"),
                    "server": response.headers.get("server"),
                    "possible_board_links": links[:50],
                    "possible_board_link_count": len(links),
                })

                print("")
                print(f"[{brand}] {probe or '/'}")
                print("Status:", response.status_code)
                print("Platform:", platform)
                print("Title:", title)
                print("Board links:", len(links))

                for item in links[:10]:
                    print(" -", item)

            except Exception as exc:

                row["error"] = str(exc)

                print("")
                print(f"[{brand}] {probe or '/'}")
                print("ERROR:", exc)

            results.append(row)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("=" * 100)
print("RECON COMPLETE")
print("=" * 100)
print("Saved:", OUTPUT_FILE)
