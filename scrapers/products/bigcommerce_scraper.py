import json
import re
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup


INPUT_FILE = Path("scrapers/retailers/active_scrape_targets.json")
OUTPUT_DIR = Path("scrapers/products/output/bigcommerce")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 QuivrrBot/1.0"
}

MAX_PRODUCT_URLS = 1200
REQUEST_TIMEOUT = 30


def safe_filename(value):
    return (
        str(value)
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("&", "and")
        .replace("'", "")
        .replace('"', "")
    )


def clear_existing_outputs():
    for file_path in OUTPUT_DIR.glob("*.json"):
        file_path.unlink()


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def get_json_ld_products(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""

        if not raw.strip():
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            graph = item.get("@graph")

            if isinstance(graph, list):
                items.extend(graph)

            item_type = item.get("@type")

            if isinstance(item_type, list):
                is_product = "Product" in item_type
            else:
                is_product = item_type == "Product"

            if is_product:
                products.append(item)

    return products


def extract_price_from_text(value):
    if value is None:
        return None

    match = re.search(r"(\d+(?:,\d{3})*(?:\.\d{1,2})?)", str(value))

    if not match:
        return None

    return match.group(1).replace(",", "")


def extract_offer(product):
    offers = product.get("offers")

    if isinstance(offers, list) and offers:
        offers = offers[0]

    if not isinstance(offers, dict):
        return {}

    return offers


def extract_images(product):
    images = product.get("image")

    if isinstance(images, str):
        return [images]

    if isinstance(images, list):
        return [
            image
            for image in images
            if isinstance(image, str) and image.strip()
        ]

    return []


def is_available_from_offer(offer):
    availability = clean(offer.get("availability")).lower()

    if not availability:
        return True

    unavailable_terms = [
        "outofstock",
        "out of stock",
        "soldout",
        "sold out",
        "discontinued",
    ]

    return not any(term in availability for term in unavailable_terms)


def extract_product_from_page(url, retailer, html):
    products = get_json_ld_products(html)

    if products:
        extracted = []

        for product in products:
            offer = extract_offer(product)
            title = clean(product.get("name"))

            if not title:
                continue

            brand = product.get("brand")

            if isinstance(brand, dict):
                brand_name = clean(brand.get("name"))
            else:
                brand_name = clean(brand)

            price = (
                offer.get("price")
                or extract_price_from_text(offer.get("priceSpecification"))
            )

            extracted.append({
                "retailer": retailer["primary_name"],
                "website": retailer["website"],
                "platform": retailer["platform"],
                "product_id": clean(product.get("sku")) or url,
                "variant_id": None,
                "title": title,
                "handle": "",
                "vendor": brand_name,
                "product_type": "",
                "variant_title": "",
                "price": clean(price),
                "compare_at_price": "",
                "available": is_available_from_offer(offer),
                "sku": clean(product.get("sku")),
                "product_url": clean(offer.get("url")) or url,
                "images": extract_images(product),
            })

        return extracted

    soup = BeautifulSoup(html, "html.parser")

    title = ""

    h1 = soup.find("h1")

    if h1:
        title = clean(h1.get_text(" "))

    if not title and soup.title:
        title = clean(soup.title.get_text(" "))

    if not title:
        return []

    image_urls = []

    og_image = soup.find("meta", property="og:image")

    if og_image and og_image.get("content"):
        image_urls.append(og_image.get("content"))

    price = None

    price_meta = soup.find("meta", property="product:price:amount")

    if price_meta and price_meta.get("content"):
        price = price_meta.get("content")

    if not price:
        price_text = soup.find(
            string=re.compile(r"\$\s*\d+(?:,\d{3})*(?:\.\d{1,2})?")
        )

        price = extract_price_from_text(price_text)

    return [{
        "retailer": retailer["primary_name"],
        "website": retailer["website"],
        "platform": retailer["platform"],
        "product_id": url,
        "variant_id": None,
        "title": title,
        "handle": "",
        "vendor": "",
        "product_type": "",
        "variant_title": "",
        "price": clean(price),
        "compare_at_price": "",
        "available": True,
        "sku": "",
        "product_url": url,
        "images": image_urls,
    }]


def sitemap_urls(base):
    candidates = [
        f"{base}/sitemap.xml",
        f"{base}/sitemap_products_1.xml",
        f"{base}/xmlsitemap.php",
    ]

    found = []

    for sitemap_url in candidates:
        try:
            response = requests.get(
                sitemap_url,
                timeout=REQUEST_TIMEOUT,
                headers=HEADERS,
            )

            if response.status_code != 200:
                continue

            root = ElementTree.fromstring(response.content)

            for element in root.iter():
                if not element.tag.endswith("loc"):
                    continue

                url = clean(element.text)

                if not url:
                    continue

                url_lower = url.lower()

                if (
                    "/products/" in url_lower
                    or "/product/" in url_lower
                    or "/surfboards/" in url_lower
                    or "surfboard" in url_lower
                ):
                    found.append(url)

        except Exception:
            continue

    return list(dict.fromkeys(found))[:MAX_PRODUCT_URLS]


def scrape_bigcommerce(retailer):
    base = retailer["website"].rstrip("/")
    product_urls = sitemap_urls(base)

    print(f"Scraping: {retailer['primary_name']}")
    print(f"  Product URLs found: {len(product_urls)}")

    all_products = []

    for index, product_url in enumerate(product_urls, start=1):
        try:
            response = requests.get(
                product_url,
                timeout=REQUEST_TIMEOUT,
                headers=HEADERS,
            )

            if response.status_code != 200:
                print(f"  [{index}/{len(product_urls)}] FAILED {response.status_code}: {product_url}")
                continue

            products = extract_product_from_page(
                product_url,
                retailer,
                response.text,
            )

            if products:
                all_products.extend(products)

        except Exception as exc:
            print(f"  [{index}/{len(product_urls)}] ERROR: {exc}")

    print(f"  Total extracted products: {len(all_products)}")

    return all_products


def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    bigcommerce_retailers = [
        retailer
        for retailer in retailers
        if retailer.get("platform") == "bigcommerce"
    ]

    print(f"BigCommerce retailers: {len(bigcommerce_retailers)}")
    print("")

    clear_existing_outputs()

    total_products = 0

    for index, retailer in enumerate(bigcommerce_retailers, start=1):
        print(f"[{index}/{len(bigcommerce_retailers)}] {retailer['primary_name']}")

        products = scrape_bigcommerce(retailer)
        total_products += len(products)

        output_file = OUTPUT_DIR / f"{safe_filename(retailer['primary_name'])}.json"

        output_file.write_text(
            json.dumps(products, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print("")
    print(f"Total extracted products: {total_products}")


if __name__ == "__main__":
    main()