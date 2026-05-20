import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


BRAND_NAME = "Chemistry Surfboards"
BASE_URL = "https://www.chemistrysurfboards.com"
CATALOGUE_URL = "https://www.chemistrysurfboards.com/shop/surfboards"
OUTPUT_FILE = Path("scrapers/brands/chemistry/output/chemistry_master_catalogue_clean.json")

CATEGORY_SLUGS = {
    "fishes",
    "high-performance",
    "legacy-series",
    "new-models",
    "performance-hybrids",
    "small-wave",
    "specialty",
    "twin-fins",
}

SIZE_PATTERN = re.compile(
    r"""(?P<length>[4-9]'\s*\d{1,2}(?:\s*1/2)?")\s+"""
    r"""(?P<width>\d{1,2}(?:\s+\d{1,2}/\d{1,2})?\s*")\s+"""
    r"""(?P<thickness>\d(?:\s+\d{1,2}/\d{1,2})?\s*")\s+"""
    r"""(?P<volume>\d{2}(?:\.\d+)?)L""",
    re.IGNORECASE,
)


def clean(value):
    value = str(value or "")
    value = value.replace("’", "'").replace("‘", "'")
    value = value.replace("″", '"').replace("”", '"').replace("“", '"')
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def normalise_length(value):
    value = clean(value)
    if not value:
        return None
    value = value.replace('"', "")
    value = value.replace(" ", "")
    return value


def normalise_dimension(value):
    value = clean(value)
    if not value:
        return None
    return value.replace('"', "").strip()


async def get_page_html(page, url):
    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(2500)
    return await page.content()


def extract_title(soup, fallback_url):
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        title = clean(meta["content"])
        title = title.replace("| Chemistry Surfboards", "").strip()
        if title.lower() not in {
            "cart is empty",
            "products comparison list - chemistry surfboards",
            "products comparison list - surfboards",
        }:
            return title

    slug = fallback_url.rstrip("/").split("/")[-1]
    return clean(slug.replace("-", " ").title())


def extract_image(soup):
    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        return clean(meta["content"])
    return None


def discover_product_urls_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    urls = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].split("?")[0].strip()
        url = urljoin(BASE_URL, href)
        parsed = urlparse(url)

        if parsed.netloc != "www.chemistrysurfboards.com":
            continue
        if not parsed.path.startswith("/shop/surfboards/"):
            continue
        if "/filter/" in parsed.path:
            continue

        slug = parsed.path.rstrip("/").split("/")[-1]
        if not slug or slug == "surfboards":
            continue
        if slug in CATEGORY_SLUGS:
            continue

        urls.add(url)

    return sorted(urls)


def extract_sizes_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    rows = []
    seen = set()

    for match in SIZE_PATTERN.finditer(text):
        length = normalise_length(match.group("length"))
        width = normalise_dimension(match.group("width"))
        thickness = normalise_dimension(match.group("thickness"))

        try:
            volume = float(match.group("volume"))
        except Exception:
            continue

        key = (length, width, thickness, volume)
        if key in seen:
            continue

        seen.add(key)
        rows.append({
            "length": length,
            "width": width,
            "thickness": thickness,
            "volume_litres": volume,
        })

    return rows


async def main():
    print("")
    print("Building Chemistry Surfboards manufacturer catalogue")
    print(f"Source: {CATALOGUE_URL}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        catalogue_html = await get_page_html(page, CATALOGUE_URL)
        product_urls = discover_product_urls_from_html(catalogue_html)

        print(f"Candidate product URLs discovered: {len(product_urls)}")

        rows = []
        seen = set()

        for url in product_urls:
            try:
                html = await get_page_html(page, url)
            except Exception as exc:
                print(f"Skipped {url}: {exc}")
                continue

            soup = BeautifulSoup(html, "html.parser")
            model = extract_title(soup, url)
            image = extract_image(soup)
            sizes = extract_sizes_from_html(html)

            if not sizes:
                print(f"No size rows: {model}")
                continue

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

        await browser.close()

    if not rows:
        raise RuntimeError("No Chemistry catalogue rows were built")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print("")
    print("Chemistry catalogue build complete")
    print(f"Models: {len(set(r['model'] for r in rows))}")
    print(f"Rows: {len(rows)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Chemistry catalogue build failed: {exc}")
        sys.exit(1)
