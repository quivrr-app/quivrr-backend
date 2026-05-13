import json
import re
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup


INPUT_FILE = Path("scrapers/retailers/active_scrape_targets.json")
OUTPUT_DIR = Path("scrapers/products/output/magento")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 QuivrrBot/1.0"
}

MAX_PRODUCT_URLS = 1500
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


def extract_price_from_text(value):
    if value is None:
        return ""

    match = re.search(
        r"(\d+(?:,\d{3})*(?:\.\d{1,2})?)",
        str(value),
    )

    if not match:
        return ""

    return match.group(1).replace(",", "")


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

        queue = data if isinstance(data, list) else [data]

        while queue:
            item = queue.pop(0)

            if not isinstance(item, dict):
                continue

            graph = item.get("@graph")

            if isinstance(graph, list):
                queue.extend(graph)

            item_type = item.get("@type")

            if isinstance(item_type, list):
                is_product = "Product" in item_type
            else:
                is_product = item_type == "Product"

            if is_product:
                products.append(item)

    return products


def extract_offer(product):
    offers = product.get("offers")

    if isinstance(offers, list) and offers:
        offers = offers[0]

    if not isinstance(offers, dict):
        return {}

    return offers


def extract_brand(product):
    brand = product.get("brand")

    if isinstance(brand, dict):
        return clean(brand.get("name"))

    return clean(brand)


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


def is_available_from_offer(offer, html):
    availability = clean(offer.get("availability")).lower()
    html_lower = html.lower()

    unavailable_terms = [
        "outofstock",
        "out of stock",
        "soldout",
        "sold out",
        "currently unavailable",
        "unavailable",
        "discontinued",
    ]

    if availability:
        return not any(
            term in availability
            for term in unavailable_terms
        )

    return not any(
        term in html_lower
        for term in unavailable_terms
    )


def extract_product_from_page(url, retailer, html):
    products = get_json_ld_products(html)

    if products:
        output = []

        for product in products:
            title = clean(product.get("name"))

            if not title:
                continue

            offer = extract_offer(product)

            price = (
                clean(offer.get("price"))
                or extract_price_from_text(offer.get("priceSpecification"))
                or extract_price_from_text(html)
            )

            output.append({
                "retailer": retailer["primary_name"],
                "website": retailer["website"],
                "platform": retailer["platform"],
                "product_id": clean(product.get("sku")) or url,
                "variant_id": None,
                "title": title,
                "handle": "",
                "vendor": extract_brand(product),
                "product_type": "",
                "variant_title": "",
                "price": price,
                "compare_at_price": "",
                "available": is_available_from_offer(offer, html),
                "sku": clean(product.get("sku")),
                "product_url": clean(offer.get("url")) or url,
                "images": extract_images(product),
            })

        return output

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

    price = ""

    price_meta = soup.find("meta", property="product:price:amount")

    if price_meta and price_meta.get("content"):
        price = clean(price_meta.get("content"))

    if not price:
        price = extract_price_from_text(html)

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
        "price": price,
        "compare_at_price": "",
        "available": is_available_from_offer({}, html),
        "sku": "",
        "product_url": url,
        "images": image_urls,
    }]


def sitemap_urls(base):
    candidates = [
        f"{base}/sitemap.xml",
        f"{base}/sitemap_products.xml",
        f"{base}/sitemap_products_1.xml",
        f"{base}/pub/sitemap.xml",
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

            nested_sitemaps = []

            for element in root.iter():
                if not element.tag.endswith("loc"):
                    continue

                url = clean(element.text)

                if not url:
                    continue

                url_lower = url.lower()

                if url_lower.endswith(".xml"):
                    nested_sitemaps.append(url)
                    continue

                if (
                    "/products/" in url_lower
                    or "/product/" in url_lower
                    or "/surfboards/" in url_lower
                    or "surfboard" in url_lower
                    or url_lower.endswith(".html")
                ):
                    found.append(url)

            for nested_url in nested_sitemaps[:30]:
                try:
                    nested_response = requests.get(
                        nested_url,
                        timeout=REQUEST_TIMEOUT,
                        headers=HEADERS,
                    )

                    if nested_response.status_code != 200:
                        continue

                    nested_root = ElementTree.fromstring(
                        nested_response.content
                    )

                    for element in nested_root.iter():
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
                            or url_lower.endswith(".html")
                        ):
                            found.append(url)

                except Exception:
                    continue

        except Exception:
            continue

    return list(dict.fromkeys(found))[:MAX_PRODUCT_URLS]


def scrape_magento(retailer):
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
                print(
                    f"  [{index}/{len(product_urls)}] "
                    f"FAILED {response.status_code}: {product_url}"
                )
                continue

            products = extract_product_from_page(
                product_url,
                retailer,
                response.text,
            )

            if products:
                all_products.extend(products)

        except Exception as exc:
            print(
                f"  [{index}/{len(product_urls)}] ERROR: {exc}"
            )

    print(f"  Total extracted products: {len(all_products)}")

    return all_products


def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    magento_retailers = [
        retailer
        for retailer in retailers
        if retailer.get("platform") == "magento"
    ]

    print(f"Magento retailers: {len(magento_retailers)}")
    print("")

    clear_existing_outputs()

    total_products = 0

    for index, retailer in enumerate(magento_retailers, start=1):
        print(f"[{index}/{len(magento_retailers)}] {retailer['primary_name']}")

        products = scrape_magento(retailer)
        total_products += len(products)

        output_file = OUTPUT_DIR / f"{safe_filename(retailer['primary_name'])}.json"

        output_file.write_text(
            json.dumps(
                products,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    print("")
    print(f"Total extracted products: {total_products}")


if __name__ == "__main__":
    main()