import html
import json
import re
import time
import urllib3
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
REQUEST_DELAY_SECONDS = 0.15

SURFBOARD_CATEGORY_HINTS = [
    "surfboard",
    "surfboards",
    "surf-surfboards",
    "performance_boards",
    "performance boards",
    "fun_boards",
    "fun boards",
    "longboards",
    "longboard",
    "shortboards",
    "shortboard",
    "softboards",
    "softboard",
    "midlength",
    "mid length",
    "fish",
    "mini mal",
    "malibu",
    "beginner surfboards",
]

SURFBOARD_CATEGORY_EXCLUDE_HINTS = [
    "accessories",
    "accessory",
    "bag",
    "bags",
    "fins",
    "leash",
    "leg rope",
    "leg-rope",
    "legrope",
    "grip",
    "wax",
    "rack",
    "repair",
    "wetsuit",
    "rash vest",
    "rash-vest",
    "rashguard",
    "bodyboard",
    "skimboard",
    "sup ",
    "sup-",
    "stand up paddle",
    "paddle board",
    "paddleboards",
    "snorkel",
    "swim",
    "skateboard",
    "skate",
    "gift card",
    "gift-card",
    "surf gear",
]

SURFBOARD_TITLE_HINTS = [
    " surfboard",
    " shortboard",
    " longboard",
    " softboard",
    " foamie",
    " funboard",
    " js ",
    " ci ",
    " lost ",
    " pyzel ",
    " firewire ",
    " dhd ",
    " chilli ",
    " sharp eye ",
    " sharpeye ",
    " slater ",
    " haydenshapes ",
    " hayden shapes ",
    " mick fanning ",
    " mf ",
]


def clean_html(value):
    if not value:
        return ""

    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    return html.unescape(text)


def normalise_price_from_value(value):
    if value is None:
        return None

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if numeric > 10000:
        numeric = numeric / 100

    return round(numeric, 2)


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


def product_looks_like_surfboard(product):
    category_text = " ".join(extract_category_names(product)).lower()
    tag_text = " ".join(extract_tag_names(product)).lower()
    title = f" {str(product.get('name') or '').lower()} "
    slug = f" {str(product.get('slug') or '').lower()} "
    combined_category_text = f"{category_text} {tag_text}"

    if any(term in combined_category_text for term in SURFBOARD_CATEGORY_HINTS):
        return True

    if any(term in title for term in SURFBOARD_TITLE_HINTS):
        return True

    if any(term.strip() in slug for term in SURFBOARD_TITLE_HINTS):
        return True

    return False


def category_looks_like_surfboard(category):
    text = " ".join(
        [
            str(category.get("name") or ""),
            str(category.get("slug") or ""),
            str(category.get("description") or ""),
        ]
    ).lower()

    if any(term in text for term in SURFBOARD_CATEGORY_EXCLUDE_HINTS):
        return False

    return any(term in text for term in SURFBOARD_CATEGORY_HINTS)


def expand_board_category_ids(categories):
    if not isinstance(categories, list):
        return []

    categories_by_id = {}
    children_by_parent = {}

    for category in categories:
        if not isinstance(category, dict):
            continue

        category_id = category.get("id")

        try:
            category_id = int(category_id)
        except (TypeError, ValueError):
            continue

        parent_id = category.get("parent")

        try:
            parent_id = int(parent_id or 0)
        except (TypeError, ValueError):
            parent_id = 0

        category_copy = dict(category)
        category_copy["id"] = category_id
        category_copy["parent"] = parent_id
        categories_by_id[category_id] = category_copy
        children_by_parent.setdefault(parent_id, []).append(category_id)

    board_ids = {
        category_id
        for category_id, category in categories_by_id.items()
        if category_looks_like_surfboard(category)
    }

    queue = list(board_ids)

    while queue:
        parent_id = queue.pop(0)
        for child_id in children_by_parent.get(parent_id, []):
            if child_id in board_ids:
                continue
            board_ids.add(child_id)
            queue.append(child_id)

    return sorted(board_ids)


def fetch_board_category_ids(base_url):
    url = f"{base_url.rstrip('/')}/wp-json/wc/store/products/categories"

    try:
        response = requests.get(
            url,
            timeout=30,
            headers=HEADERS,
            verify=False,
        )
    except Exception:
        return []

    if response.status_code != 200:
        return []

    try:
        categories = response.json()
    except Exception:
        return []

    return expand_board_category_ids(categories)


def format_size_token(value):
    if value is None:
        return ""

    raw = str(value).strip().lower()
    raw = raw.replace("ft", "").replace("feet", "")
    raw = raw.replace("’", "'").replace('"', "")
    raw = raw.replace("-", "").replace("_", "")

    if "'" in raw:
        return raw

    digits = re.sub(r"[^0-9]", "", raw)

    if len(digits) == 2:
        return f"{digits[0]}'{digits[1]}"

    if len(digits) == 3 and digits[1:] in {"10", "11", "12"}:
        return f"{digits[0]}'{digits[1:]}"

    return str(value).strip()


def extract_variation_attributes(variation):
    attributes = variation.get("attributes") or {}
    values = []

    if isinstance(attributes, dict):
        for key, value in attributes.items():
            clean_key = str(key).replace("attribute_pa_", "").replace("attribute_", "")
            clean_key = clean_key.replace("_", " ").replace("-", " ").title()

            if clean_key.lower() == "size":
                clean_value = format_size_token(value)
            else:
                clean_value = str(value).replace("-", " ").title()

            if clean_value:
                values.append(f"{clean_key} {clean_value}")

    return " ".join(values).strip()


def variation_is_available(variation):
    if variation.get("variation_is_active") is False:
        return False

    if variation.get("variation_is_visible") is False:
        return False

    if variation.get("is_purchasable") is False:
        return False

    if variation.get("is_in_stock") is True:
        return True

    availability_html = clean_html(variation.get("availability_html")).lower()

    if "in stock" in availability_html:
        return True

    return False


def extract_variation_image_urls(variation):
    image = variation.get("image") or {}

    if not isinstance(image, dict):
        return []

    urls = []

    for key in ["src", "url", "full_src"]:
        value = image.get(key)

        if value:
            urls.append(value)

    return list(dict.fromkeys(urls))


def get_product_variations_from_page(product_url):
    if not product_url:
        return []

    try:
        response = requests.get(
            product_url,
            timeout=30,
            headers=HEADERS,
            verify=False,
        )

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        forms = soup.select("form.variations_form")

        for form in forms:
            raw = form.get("data-product_variations")

            if not raw:
                continue

            decoded = html.unescape(raw)
            variations = json.loads(decoded)

            if isinstance(variations, list):
                return variations

    except Exception:
        return []

    return []


def build_base_product(product, retailer):
    category_names = extract_category_names(product)
    tag_names = extract_tag_names(product)
    attribute_text = extract_attribute_text(product)

    short_description = clean_html(product.get("short_description"))
    description = clean_html(product.get("description"))

    title = product.get("name") or ""
    slug = product.get("slug") or ""
    permalink = product.get("permalink") or ""

    return {
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


def build_variation_product(base_product, variation):
    output = dict(base_product)

    variation_attributes = extract_variation_attributes(variation)
    variation_images = extract_variation_image_urls(variation)

    variation_price = normalise_price_from_value(
        variation.get("display_price")
        or variation.get("display_regular_price")
    )

    output["variant_id"] = variation.get("variation_id")
    output["variant_title"] = variation_attributes
    output["price"] = variation_price if variation_price is not None else base_product.get("price")
    output["compare_at_price"] = normalise_price_from_value(
        variation.get("display_regular_price")
    )
    output["available"] = variation_is_available(variation)
    output["sku"] = variation.get("sku") or base_product.get("sku")
    output["images"] = variation_images or base_product.get("images", [])

    return output


def dedupe_products(products):
    seen = set()
    output = []

    for product in products:
        key = (
            product.get("retailer"),
            product.get("product_id"),
            product.get("variant_id"),
            product.get("title"),
            product.get("variant_title"),
            product.get("sku"),
            product.get("product_url"),
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(product)

    return output


def extract_products(products, retailer):
    output = []

    for product in products:
        base_product = build_base_product(product, retailer)

        should_expand_variations = (
            product_looks_like_surfboard(product)
            and product.get("type") == "variable"
            and base_product.get("product_url")
        )

        if should_expand_variations:
            variations = get_product_variations_from_page(base_product["product_url"])
            time.sleep(REQUEST_DELAY_SECONDS)

            if variations:
                for variation in variations:
                    output.append(build_variation_product(base_product, variation))

                continue

        output.append(base_product)

    return output


def scrape_woocommerce(retailer):
    base = retailer["website"].rstrip("/")
    board_category_ids = fetch_board_category_ids(base)
    category_query = ""

    if board_category_ids:
        category_query = "&category=" + ",".join(
            str(category_id)
            for category_id in board_category_ids
        )

    page = 1
    all_products = []

    print(f"Scraping: {retailer['primary_name']}")
    if board_category_ids:
        print(
            "  Category filter ids: "
            + ",".join(str(category_id) for category_id in board_category_ids)
        )

    while True:
        url = (
            f"{base}/wp-json/wc/store/products"
            f"?page={page}"
            f"&per_page={PER_PAGE}"
            f"{category_query}"
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

    all_products = dedupe_products(all_products)

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
        .replace("'", "")
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
