import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


INPUT_FILE = Path("scrapers/retailers/active_scrape_targets.json")
FALLBACK_INPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets_classified.json")
OUTPUT_DIR = Path("scrapers/products/output/woocommerce")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,*/*",
}

PER_PAGE = 100


def clean_html(value):
    if not value:
        return ""

    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalise_price(product):
    prices = product.get("prices") or {}

    raw_price = (
        prices.get("price")
        or product.get("price")
        or product.get("regular_price")
    )

    if raw_price is None:
        return None

    try:
        numeric = float(raw_price)
    except (TypeError, ValueError):
        return None

    minor_unit = prices.get("currency_minor_unit", 2)

    try:
        minor_unit = int(minor_unit)
    except (TypeError, ValueError):
        minor_unit = 2

    if numeric > 1000 and minor_unit > 0:
        numeric = numeric / (10 ** minor_unit)

    return round(numeric, 2)


def extract_image_urls(product):
    images = product.get("images", [])
    image_urls = []

    for image in images:
        if isinstance(image, dict):
            src = image.get("src")

            if src:
                image_urls.append(src)

    return image_urls


def extract_category_names(product):
    categories = product.get("categories", [])
    names = []

    for category in categories:
        if isinstance(category, dict):
            name = category.get("name")
            slug = category.get("slug")

            if name:
                names.append(str(name))

            if slug:
                names.append(str(slug))

    return list(dict.fromkeys(names))


def extract_tag_names(product):
    tags = product.get("tags", [])
    names = []

    for tag in tags:
        if isinstance(tag, dict):
            name = tag.get("name")
            slug = tag.get("slug")

            if name:
                names.append(str(name))

            if slug:
                names.append(str(slug))

    return list(dict.fromkeys(names))


def extract_attribute_text(product):
    attributes = product.get("attributes", [])
    values = []

    for attribute in attributes:
        if not isinstance(attribute, dict):
            continue

        name = attribute.get("name")
        value = attribute.get("value")
        terms = attribute.get("terms")

        if name:
            values.append(str(name))

        if value:
            values.append(clean_html(value))

        if isinstance(terms, list):
            for term in terms:
                if isinstance(term, dict):
                    term_name = term.get("name")
                    term_slug = term.get("slug")

                    if term_name:
                        values.append(str(term_name))

                    if term_slug:
                        values.append(str(term_slug))

                elif term:
                    values.append(str(term))

    return " ".join([v for v in values if v]).strip()


def is_product_available(product):
    stock_status = product.get("stock_status")
    is_purchasable = product.get("is_purchasable")
    is_in_stock = product.get("is_in_stock")

    available = False

    if stock_status == "instock":
        available = True

    if is_in_stock is True:
        available = True

    if is_purchasable is False:
        available = False

    return available


def extract_products(products, retailer):
    output = []

    for product in products:
        category_names = extract_category_names(product)
        tag_names = extract_tag_names(product)
        attribute_text = extract_attribute_text(product)

        short_description = clean_html(product.get("short_description"))
        description = clean_html(product.get("description"))

        title = product.get("name") or ""
        slug = product.get("slug") or ""
        permalink = product.get("permalink") or ""

        output.append(
            {
                "retailer": retailer["primary_name"],
                "website": retailer["website"],
                "platform": retailer["platform"],
                "product_id": product.get("id"),
                "variant_id": None,
                "title": title,
                "handle": slug,
                "vendor": "",
                "product_type": " ".join(category_names),
                "categories": category_names,
                "tags": tag_names,
                "variant_title": attribute_text,
                "description": description,
                "short_description": short_description,
                "price": normalise_price(product),
                "compare_at_price": None,
                "available": is_product_available(product),
                "sku": product.get("sku"),
                "product_url": permalink,
                "images": extract_image_urls(product),
            }
        )

    return output


def scrape_woocommerce(retailer):
    base = retailer["website"].rstrip("/")

    page = 1
    all_products = []

    print(f"Scraping: {retailer['primary_name']}")

    while True:
        url = (
            f"{base}/wp-json/wc/store/products"
            f"?page={page}"
            f"&per_page={PER_PAGE}"
        )

        try:
            response = requests.get(
                url,
                timeout=30,
                headers=HEADERS,
                verify=False,
            )

            if response.status_code != 200:
                print(f"  ERROR page {page}: {response.status_code}")
                break

            products = response.json()

            if not products:
                break

            print(f"  Page {page}: {len(products)} products")

            extracted = extract_products(products, retailer)
            all_products.extend(extracted)

            if len(products) < PER_PAGE:
                break

            page += 1

        except Exception as exc:
            print(f"  ERROR page {page}: {exc}")
            break

    print(f"  Total products: {len(all_products)}")

    return all_products


def load_retailers():
    input_file = INPUT_FILE

    if not input_file.exists():
        input_file = FALLBACK_INPUT_FILE

    return json.loads(input_file.read_text(encoding="utf-8"))


def safe_filename(name):
    return (
        name.lower()
        .replace("&", "and")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )


def main():
    retailers = load_retailers()

    woocommerce_retailers = [
        retailer for retailer in retailers
        if retailer.get("platform") == "woocommerce"
    ]

    print(f"WooCommerce retailers: {len(woocommerce_retailers)}")
    print("")

    total_products = 0

    for retailer in woocommerce_retailers:
        products = scrape_woocommerce(retailer)
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