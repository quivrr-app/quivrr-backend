import argparse
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


RETAILER_NAME = "Coopers Board Store"
BASE_URL = "https://coopersboardstore.com.au"

OUTPUT_DIR = Path("scrapers/products/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "coopers_board_store_raw_inventory.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    )
}

EXCLUDED_SLUG_PARTS = [
    "test-product",
    "/test/",
    "/test-2/",
]

TEST_PRODUCT_URLS = [
    "https://coopersboardstore.com.au/product/7s-double-down-pu-2/",
    "https://coopersboardstore.com.au/product/7s-superfish-4-pu/",
    "https://coopersboardstore.com.au/product/91-isha-longboard/",
    "https://coopersboardstore.com.au/product/aloha-funzarelli-ecoskin-black/",
    "https://coopersboardstore.com.au/product/aloha-habanero-ii-pu/",
    "https://coopersboardstore.com.au/product/js-xero-gravity-hyfi-3-0/",
]


def clean_text(value):
    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def normalise_quotes(value):
    if not value:
        return ""

    return (
        value
        .replace("’", "'")
        .replace("‘", "'")
        .replace("”", '"')
        .replace("“", '"')
    )


def get_product_sitemap_urls():
    response = requests.get(
        f"{BASE_URL}/sitemap.xml",
        headers=HEADERS,
        timeout=60,
        allow_redirects=True,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "xml")

    sitemap_urls = []

    for loc in soup.find_all("loc"):
        value = loc.get_text(strip=True)

        if "product-sitemap" in value:
            sitemap_urls.append(value)

    return sorted(set(sitemap_urls))


def get_product_urls():
    product_urls = []

    for sitemap_url in get_product_sitemap_urls():
        print(f"Reading sitemap: {sitemap_url}")

        response = requests.get(
            sitemap_url,
            headers=HEADERS,
            timeout=60,
            allow_redirects=True,
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "xml")

        for loc in soup.find_all("loc"):
            value = loc.get_text(strip=True)

            if "/product/" in value:
                product_urls.append(value)

    return sorted(set(product_urls))


def extract_price(html):
    patterns = [
        r"\$([0-9][0-9,\.]+)",
        r'"price"\s*:\s*"?(?P<price>[0-9]+(?:\.[0-9]+)?)"?',
    ]

    for pattern in patterns:
        match = re.search(pattern, html)

        if match:
            if "price" in match.groupdict():
                return match.group("price")

            return match.group(1)

    return None


def extract_title(soup):
    h1 = soup.find("h1")

    if h1:
        return clean_text(h1.get_text(" ", strip=True))

    title_tag = soup.find("title")

    if title_tag:
        return clean_text(title_tag.get_text(" ", strip=True))

    return ""


def extract_availability_text(soup):
    candidates = []

    selectors = [
        ".stock",
        ".availability",
        ".woocommerce-variation-availability",
        ".summary",
        "form.variations_form",
    ]

    for selector in selectors:
        for element in soup.select(selector):
            text = clean_text(element.get_text(" ", strip=True))

            if text:
                candidates.append(text)

    return " | ".join(dict.fromkeys(candidates))


def looks_like_slug_variant(value):
    lower_value = value.lower()

    if re.fullmatch(r"[0-9a-z\-]+", lower_value) and "-" in lower_value:
        return True

    return False


def looks_like_dimension_variant(value):
    lower_value = normalise_quotes(value).lower()

    has_length = re.search(r"\b[4-9]'[0-9]{1,2}\"?", lower_value)
    has_volume = re.search(
        r"\b[0-9]{2}(?:\.[0-9]+)?\s?(?:l|litres?)\b",
        lower_value,
    )

    return bool(has_length or has_volume)


def extract_raw_variant_values(soup):
    values = []

    for option in soup.select("select option"):
        text = clean_text(option.get_text(" ", strip=True))

        if not text:
            continue

        if text.lower() in ["choose an option", "select option", "default"]:
            continue

        values.append(text)

    selectors = [
        ".variable-item",
        ".variable-item-span",
        ".swatch",
        ".button-variable-item",
        "[data-value]",
        "[data-title]",
    ]

    for selector in selectors:
        for element in soup.select(selector):
            for value in [
                clean_text(element.get_text(" ", strip=True)),
                clean_text(element.get("data-value", "")),
                clean_text(element.get("data-title", "")),
            ]:
                if value:
                    values.append(value)

    return values


def extract_variant_options(soup):
    options = []

    for value in extract_raw_variant_values(soup):
        value = clean_text(value)

        if not value:
            continue

        if value.lower() in ["add to cart", "buy now", "read more"]:
            continue

        if looks_like_slug_variant(value):
            continue

        if not looks_like_dimension_variant(value):
            continue

        options.append(value)

    return sorted(set(options))


def extract_length(value):
    if not value:
        return None

    normalised = normalise_quotes(value)

    match = re.search(r"\b([4-9]'[0-9]{1,2})\"?", normalised)

    if match:
        return match.group(1)

    return None


def extract_volume_litres(value):
    if not value:
        return None

    lower_value = normalise_quotes(value).lower()

    matches = re.findall(
        r"\b([0-9]{2}(?:\.[0-9]+)?)\s?(?:l|litres?)\b",
        lower_value,
    )

    if not matches:
        return None

    try:
        return float(matches[-1])
    except ValueError:
        return None


def is_excluded_url(url):
    lower_url = url.lower()

    return any(part in lower_url for part in EXCLUDED_SLUG_PARTS)


def dedupe_rows(rows):
    seen = set()
    deduped = []

    for row in rows:
        key = (
            row.get("product_url"),
            row.get("title"),
            row.get("length"),
            row.get("volume_litres"),
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    return deduped


def extract_product_data(url):
    if is_excluded_url(url):
        return []

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=60,
            allow_redirects=True,
        )

        base_item = {
            "retailer": RETAILER_NAME,
            "retailer_url": BASE_URL,
            "product_url": url,
            "available": response.status_code == 200,
            "source": "coopers_product_sitemap",
            "status_code": response.status_code,
        }

        if response.status_code != 200:
            return [base_item]

        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        title = extract_title(soup)
        price = extract_price(html)
        availability_text = extract_availability_text(soup)
        variant_options = extract_variant_options(soup)

        base_item.update(
            {
                "title": title,
                "price": price,
                "availability_text": availability_text,
            }
        )

        if not variant_options:
            return [base_item]

        rows = []

        for option in variant_options:
            row = dict(base_item)
            row["variant"] = option
            row["length"] = extract_length(option)
            row["volume_litres"] = extract_volume_litres(option)
            rows.append(row)

        return dedupe_rows(rows)

    except Exception as error:
        return [
            {
                "retailer": RETAILER_NAME,
                "retailer_url": BASE_URL,
                "product_url": url,
                "available": False,
                "source": "coopers_product_sitemap",
                "error": str(error),
            }
        ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run against selected Coopers problem pages only.",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Coopers Board Store inventory scrape")
    print("=" * 60)

    if args.test:
        print("Mode: test")
        product_urls = TEST_PRODUCT_URLS
    else:
        print("Mode: full")
        product_urls = get_product_urls()

    print(f"Product URLs found: {len(product_urls)}")

    results = []

    for index, url in enumerate(product_urls, start=1):
        print(f"[{index}/{len(product_urls)}] {url}")

        items = extract_product_data(url)
        results.extend(items)

        time.sleep(0.5)

    results = dedupe_rows(results)

    OUTPUT_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    variant_rows = sum(1 for item in results if item.get("variant"))
    length_rows = sum(1 for item in results if item.get("length"))
    volume_rows = sum(1 for item in results if item.get("volume_litres"))

    print()
    print(f"Inventory rows collected: {len(results)}")
    print(f"Variant rows collected: {variant_rows}")
    print(f"Rows with length: {length_rows}")
    print(f"Rows with volume: {volume_rows}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()