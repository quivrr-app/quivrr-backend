import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests


OUTPUT_DIR = Path("scrapers/retailers/recon_focused")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {
        "name": "Coopers Surf",
        "base_url": "https://cooperssurf.com.au",
        "sitemap_url": "https://cooperssurf.com.au/sitemap_index.xml",
    },
    {
        "name": "Coopers Board Store",
        "base_url": "https://coopersboardstore.com.au",
        "sitemap_url": "https://coopersboardstore.com.au/sitemap_index.xml",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/0.1; +https://quivrr.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def fetch(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True,
        )

        return {
            "ok": True,
            "url": url,
            "final_url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "text": response.text[:500000],
            "length": len(response.text or ""),
        }

    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "error": str(exc),
        }


def parse_sitemap_locations(xml_text):
    locations = []

    try:
        root = ET.fromstring(xml_text.encode("utf-8"))

        for loc in root.findall(".//sm:loc", NS):
            if loc.text:
                locations.append(loc.text.strip())

    except Exception:
        return []

    return locations


def run_target(target):
    print("")
    print("=" * 80)
    print(target["name"])
    print("=" * 80)

    result = {
        "target": target["name"],
        "base_url": target["base_url"],
        "sitemap_url": target["sitemap_url"],
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "sitemap_index": None,
        "product_sitemaps": [],
        "sample_products": [],
    }

    sitemap_index = fetch(target["sitemap_url"])
    result["sitemap_index"] = {
        key: value
        for key, value in sitemap_index.items()
        if key != "text"
    }

    print(
        f"Sitemap index: {sitemap_index.get('status_code')} "
        f"{sitemap_index.get('content_type', '')} "
        f"length={sitemap_index.get('length')}"
    )

    if not sitemap_index.get("ok") or sitemap_index.get("status_code") != 200:
        return result

    sitemap_locations = parse_sitemap_locations(sitemap_index["text"])

    product_sitemaps = [
        url for url in sitemap_locations
        if "product-sitemap" in url
    ]

    for sitemap_url in product_sitemaps:
        time.sleep(1)

        sitemap_response = fetch(sitemap_url)
        product_urls = []

        if sitemap_response.get("ok") and sitemap_response.get("status_code") == 200:
            product_urls = parse_sitemap_locations(sitemap_response["text"])

        print(
            f"Product sitemap: {sitemap_url} "
            f"status={sitemap_response.get('status_code')} "
            f"products={len(product_urls)}"
        )

        result["product_sitemaps"].append(
            {
                "url": sitemap_url,
                "status_code": sitemap_response.get("status_code"),
                "content_type": sitemap_response.get("content_type"),
                "length": sitemap_response.get("length"),
                "product_url_count": len(product_urls),
                "sample_urls": product_urls[:10],
            }
        )

        for product_url in product_urls[:5]:
            time.sleep(1)

            product_response = fetch(product_url)

            title = ""
            text = product_response.get("text") or ""

            marker_start = text.lower().find("<title>")
            marker_end = text.lower().find("</title>")

            if marker_start >= 0 and marker_end > marker_start:
                title = text[marker_start + len("<title>"):marker_end].strip()

            print(
                f"Sample product: {product_response.get('status_code')} "
                f"{product_url}"
            )

            result["sample_products"].append(
                {
                    "url": product_url,
                    "status_code": product_response.get("status_code"),
                    "content_type": product_response.get("content_type"),
                    "length": product_response.get("length"),
                    "title": title,
                }
            )

    return result


def main():
    results = []

    for target in TARGETS:
        results.append(run_target(target))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    json_path = OUTPUT_DIR / f"coopers_azure_probe_{timestamp}.json"
    txt_path = OUTPUT_DIR / f"coopers_azure_probe_{timestamp}.txt"

    json_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = []

    for result in results:
        lines.append("")
        lines.append(result["target"])
        lines.append("=" * len(result["target"]))
        lines.append(f"Sitemap: {result['sitemap_index']}")

        for sitemap in result["product_sitemaps"]:
            lines.append(
                f"Product sitemap: {sitemap['url']} "
                f"status={sitemap['status_code']} "
                f"products={sitemap['product_url_count']}"
            )

        for product in result["sample_products"]:
            lines.append(
                f"Sample product: {product['status_code']} "
                f"{product['url']} "
                f"{product['title']}"
            )

    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print("")
    print("Saved:")
    print(json_path)
    print(txt_path)


if __name__ == "__main__":
    main()
