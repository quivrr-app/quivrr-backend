import argparse
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


RETAILER_NAME = "Coopers Board Store"
BASE_URL = "https://coopersboardstore.com.au"

OUTPUT_DIR = Path("scrapers/products/output/coopers")
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

IMAGE_REJECT_TERMS = [
    "leash",
    "legrope",
    "leg-rope",
    "traction",
    "tail-pad",
    "tailpad",
    "grip",
    "wax",
    "fin",
    "fins",
    "cover",
    "bag",
    "sock",
    "strap",
    "tie-down",
    "wetsuit",
    "steamer",
    "rash",
    "oe-6ft-flex",
    "diamond-flex",
    "regular-diamond",
    "premium-one-xt",
]

IMAGE_PREFERRED_TERMS = [
    "monsta",
    "xero",
    "gravity",
    "fusion",
    "black-baron",
    "baron",
    "raging-bull",
    "bull",
    "blak-box",
    "air-17",
    "golden-child",
    "sub-xero",
    "surfboard",
    "board",
    "main",
]

TEST_PRODUCT_URLS = [
    "https://coopersboardstore.com.au/product/7s-double-down-pu-2/",
    "https://coopersboardstore.com.au/product/7s-superfish-4-pu/",
    "https://coopersboardstore.com.au/product/91-isha-longboard/",
    "https://coopersboardstore.com.au/product/aloha-funzarelli-ecoskin-black/",
    "https://coopersboardstore.com.au/product/aloha-habanero-ii-pu/",
    "https://coopersboardstore.com.au/product/js-xero-gravity-carbotune/",
    "https://coopersboardstore.com.au/product/js-xero-gravity-hyfi-3-0/",
    "https://coopersboardstore.com.au/product/monsta-pu-fcsii/",
]


def clean_text(value):
    if not value:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def normalise_quotes(value):
    if not value:
        return ""

    return (
        str(value)
        .replace("’", "'")
        .replace("‘", "'")
        .replace("″", '"')
        .replace("“", '"')
        .replace("”", '"')
        .replace("′", "'")
        .replace("â€™", "'")
        .replace("â€˜", "'")
        .replace("â€", '"')
        .replace("â€œ", '"')
    )


def normalise_price(value):
    if value is None:
        return None

    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def absolute_url(value):
    if not value:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value.startswith("//"):
        return f"https:{value}"

    return urljoin(BASE_URL, value)


def valid_image_url(value):
    url = absolute_url(value)

    if not url:
        return None

    lowered = url.lower()

    if not lowered.startswith(("http://", "https://")):
        return None

    if any(skip in lowered for skip in [
        "placeholder",
        "logo",
        "icon",
        "sprite",
        "avatar",
        "payment",
        "afterpay",
        "zip-pay",
        "loading",
        "blank",
    ]):
        return None

    if not any(ext in lowered for ext in [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    ]):
        return None

    return url


def first_valid_image_url(values):
    for value in values:
        url = valid_image_url(value)

        if url:
            return url

    return None


def slug_tokens_from_title(title):
    text = clean_text(title).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    tokens = [
        token
        for token in text.split("-")
        if token
        and len(token) >= 3
        and token not in ["the", "and", "with", "fcs", "fcsii", "fcs2", "pu", "eps"]
    ]

    return tokens


def image_score(image_url, title):
    if not image_url:
        return -1000

    lowered = image_url.lower()
    score = 0

    if "/wp-content/uploads/" in lowered:
        score += 20

    if any(term in lowered for term in IMAGE_REJECT_TERMS):
        score -= 80

    if any(term in lowered for term in IMAGE_PREFERRED_TERMS):
        score += 20

    title_tokens = slug_tokens_from_title(title)

    for token in title_tokens:
        if token in lowered:
            score += 15

    if "main" in lowered:
        score += 8

    if "front" in lowered:
        score += 6

    if "back" in lowered:
        score += 4

    if "346x461" in lowered or "300x300" in lowered:
        score -= 5

    if "1536" in lowered or "2048" in lowered:
        score += 5

    return score


def rank_images(image_urls, title):
    unique_images = []

    for image_url in image_urls:
        valid_url = valid_image_url(image_url)

        if valid_url and valid_url not in unique_images:
            unique_images.append(valid_url)

    return sorted(
        unique_images,
        key=lambda value: image_score(value, title),
        reverse=True,
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
        print(f"Reading sitemap: {sitemap_url}", flush=True)

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


def extract_price_from_json_ld(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        raw = clean_text(script.string or script.get_text())

        if not raw:
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            offers = item.get("offers")

            if isinstance(offers, dict):
                price = normalise_price(offers.get("price"))

                if price:
                    return price

            if isinstance(offers, list):
                for offer in offers:
                    if isinstance(offer, dict):
                        price = normalise_price(offer.get("price"))

                        if price:
                            return price

    return None


def extract_images_from_json_ld(soup):
    image_urls = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = clean_text(script.string or script.get_text())

        if not raw:
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            image = item.get("image")

            if isinstance(image, str):
                image_urls.append(image)

            if isinstance(image, list):
                image_urls.extend(image)

            if isinstance(image, dict):
                image_urls.extend([
                    image.get("url"),
                    image.get("@id"),
                    image.get("contentUrl"),
                ])

    return [
        image_url
        for image_url in image_urls
        if valid_image_url(image_url)
    ]


def extract_product_images(soup, title):
    image_candidates = []

    priority_selectors = [
        ".woocommerce-product-gallery__image img",
        ".product .images img",
        ".wp-post-image",
        "img.wp-post-image",
    ]

    fallback_selectors = [
        ".summary img",
        "img",
    ]

    for selector in priority_selectors:
        for image in soup.select(selector):
            image_candidates.extend([
                image.get("data-large_image"),
                image.get("data-o_src"),
                image.get("src"),
                image.get("data-src"),
                image.get("data-lazy-src"),
            ])

            srcset = image.get("srcset") or image.get("data-srcset")

            if srcset:
                for part in srcset.split(","):
                    image_candidates.append(part.strip().split(" ")[0])

    for meta_property in [
        "og:image",
        "og:image:secure_url",
        "twitter:image",
    ]:
        meta = soup.find("meta", property=meta_property)

        if meta:
            image_candidates.append(meta.get("content"))

        meta = soup.find("meta", attrs={"name": meta_property})

        if meta:
            image_candidates.append(meta.get("content"))

    image_candidates.extend(extract_images_from_json_ld(soup))

    for selector in fallback_selectors:
        for image in soup.select(selector):
            image_candidates.extend([
                image.get("data-large_image"),
                image.get("data-o_src"),
                image.get("src"),
                image.get("data-src"),
                image.get("data-lazy-src"),
            ])

            srcset = image.get("srcset") or image.get("data-srcset")

            if srcset:
                for part in srcset.split(","):
                    image_candidates.append(part.strip().split(" ")[0])

    return rank_images(image_candidates, title)


def extract_variation_image(variation):
    if not isinstance(variation, dict):
        return None

    image = variation.get("image")

    if isinstance(image, dict):
        return first_valid_image_url([
            image.get("full_src"),
            image.get("src"),
            image.get("url"),
            image.get("thumb_src"),
            image.get("gallery_thumbnail_src"),
        ])

    if isinstance(image, str):
        return valid_image_url(image)

    return None


def extract_price_from_page(soup, html_text):
    summary_price = soup.select_one(".summary .price")
    if summary_price:
        price_text = clean_text(summary_price.get_text(" ", strip=True))
        matches = re.findall(r"\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)", price_text)

        if matches:
            prices = [
                normalise_price(match)
                for match in matches
                if normalise_price(match) is not None
            ]

            if prices:
                return max(prices)

    json_ld_price = extract_price_from_json_ld(soup)

    if json_ld_price:
        return json_ld_price

    matches = re.findall(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)", html_text)

    prices = [
        normalise_price(match)
        for match in matches
        if normalise_price(match) is not None
    ]

    prices = [
        price
        for price in prices
        if price >= 250
    ]

    if prices:
        return max(prices)

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


def extract_variation_json(soup):
    variations = []

    for form in soup.select("form.variations_form"):
        raw = form.get("data-product_variations")

        if not raw:
            continue

        decoded = html.unescape(raw)

        try:
            data = json.loads(decoded)
        except json.JSONDecodeError:
            continue

        if isinstance(data, list):
            variations.extend(data)

    return variations


def compact_length_from_slug(value):
    if not value:
        return None

    value = str(value).lower()

    match = re.search(r"(?<![0-9])([4-9])([0-9]{1,2})(?![0-9])", value)

    if not match:
        return None

    feet = match.group(1)
    inches = match.group(2)

    try:
        inches_int = int(inches)
    except ValueError:
        return None

    if inches_int > 12:
        return None

    return f"{feet}'{inches_int}"


def format_fraction_dimension(tokens):
    clean_tokens = [
        str(token).strip()
        for token in tokens
        if str(token).strip()
    ]

    if not clean_tokens:
        return None

    if len(clean_tokens) == 1:
        return clean_tokens[0]

    if len(clean_tokens) == 2:
        return f"{clean_tokens[0]} {clean_tokens[1]}"

    return f"{clean_tokens[0]} {clean_tokens[1]}/{clean_tokens[2]}"


def parse_compact_dimension_slug(value):
    if not value:
        return {}

    lower_value = normalise_quotes(value).lower()

    candidates = re.findall(
        r"\b[4-9][0-9]{2}(?:-[0-9]+)+-[1-8][0-9]-[0-9]+l\b",
        lower_value,
    )

    if not candidates:
        return {}

    candidate = candidates[-1]
    parts = candidate.rstrip("l").split("-")

    if len(parts) < 5:
        return {}

    length_token = parts[0]
    volume_whole = parts[-2]
    volume_decimal = parts[-1]
    dimension_tokens = parts[1:-2]

    length = compact_length_from_slug(length_token)

    try:
        volume_litres = float(f"{volume_whole}.{volume_decimal}")
    except ValueError:
        volume_litres = None

    thickness_start_index = None

    for index, token in enumerate(dimension_tokens):
        if token in ["2", "3"]:
            thickness_start_index = index
            break

    if thickness_start_index is None:
        width_tokens = dimension_tokens[:1]
        thickness_tokens = dimension_tokens[1:]
    else:
        width_tokens = dimension_tokens[:thickness_start_index]
        thickness_tokens = dimension_tokens[thickness_start_index:]

    width = format_fraction_dimension(width_tokens)
    thickness = format_fraction_dimension(thickness_tokens)

    return {
        "length": length,
        "width": width,
        "thickness": thickness,
        "volume_litres": volume_litres,
    }


def parse_pipe_dimension_text(value):
    if not value:
        return {}

    normalised = normalise_quotes(value)

    parts = [
        clean_text(part)
        for part in normalised.split("|")
        if clean_text(part)
    ]

    if len(parts) < 2:
        return {}

    length = None
    width = None
    thickness = None
    volume_litres = None

    for part in parts:
        if length is None:
            length = extract_length(part)

        if volume_litres is None:
            volume_litres = extract_volume_litres(part)

    if looks_like_dimension_variant(parts[0]):
        length = extract_length(parts[0]) or length

    dimension_parts = [
        part
        for part in parts
        if looks_like_dimension_variant(part)
        or re.search(r"[0-9]", part)
    ]

    if len(dimension_parts) >= 2:
        width = dimension_parts[1]

    if len(dimension_parts) >= 3:
        thickness = dimension_parts[2]

    return {
        "length": length,
        "width": width,
        "thickness": thickness,
        "volume_litres": volume_litres,
    }


def parse_dimension_values(value):
    compact = parse_compact_dimension_slug(value)

    if compact:
        return compact

    return parse_pipe_dimension_text(value)


def extract_length(value):
    if not value:
        return None

    normalised = normalise_quotes(value)

    match = re.search(r"\b([4-9]'[0-9]{1,2})\"?", normalised)

    if match:
        return match.group(1)

    parsed = parse_compact_dimension_slug(normalised)

    if parsed.get("length"):
        return parsed["length"]

    return compact_length_from_slug(normalised)


def extract_volume_litres(value):
    if not value:
        return None

    lower_value = normalise_quotes(value).lower()

    matches = re.findall(
        r"\b([0-9]{2}(?:\.[0-9]+)?)\s?(?:l|ltr|litre|litres)\b",
        lower_value,
    )

    if matches:
        try:
            return float(matches[-1])
        except ValueError:
            return None

    parsed = parse_compact_dimension_slug(lower_value)

    if parsed.get("volume_litres") is not None:
        return parsed["volume_litres"]

    compact_matches = re.findall(
        r"\b([1-8][0-9])-([0-9]{1,2})l\b",
        lower_value,
    )

    if compact_matches:
        whole, decimal = compact_matches[-1]

        try:
            return float(f"{whole}.{decimal}")
        except ValueError:
            return None

    return None


def extract_width(value):
    if not value:
        return None

    parsed = parse_dimension_values(value)

    if parsed.get("width"):
        return parsed["width"]

    normalised = normalise_quotes(value)

    parts = [
        clean_text(part)
        for part in normalised.split("|")
    ]

    if len(parts) >= 2:
        return parts[1]

    return None


def extract_thickness(value):
    if not value:
        return None

    parsed = parse_dimension_values(value)

    if parsed.get("thickness"):
        return parsed["thickness"]

    normalised = normalise_quotes(value)

    parts = [
        clean_text(part)
        for part in normalised.split("|")
    ]

    if len(parts) >= 3:
        return parts[2]

    return None


def extract_stock_quantity(value):
    if not value:
        return None

    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)

    match = re.search(r"\b([0-9]+)\s+in stock\b", text, re.IGNORECASE)

    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None

    return None


def is_in_stock(variation):
    if not isinstance(variation, dict):
        return False

    if variation.get("is_in_stock") is True:
        return True

    availability_html = variation.get("availability_html") or ""

    return "in-stock" in availability_html or "in stock" in availability_html.lower()


def variation_attribute_text(variation):
    attributes = variation.get("attributes")

    if not isinstance(attributes, dict):
        return ""

    values = []

    preferred_keys = [
        "attribute_pa_size",
        "attribute_size",
        "attribute_sizes",
        "attribute_pa_sizes",
        "attribute_pa_brand",
        "attribute_brand",
    ]

    for key in preferred_keys:
        value = attributes.get(key)

        if value:
            values.append(value)

    for value in attributes.values():
        if value:
            values.append(value)

    return " | ".join(dict.fromkeys([clean_text(value) for value in values if value]))


def looks_like_slug_variant(value):
    lower_value = str(value).lower()

    return bool(re.fullmatch(r"[0-9a-z\-]+", lower_value) and "-" in lower_value)


def looks_like_dimension_variant(value):
    lower_value = normalise_quotes(value).lower()

    has_length = re.search(r"\b[4-9]'[0-9]{1,2}\"?", lower_value)
    has_compact_length = compact_length_from_slug(lower_value) is not None
    has_volume = re.search(
        r"\b[0-9]{2}(?:\.[0-9]+)?\s?(?:l|litres?|ltr)\b",
        lower_value,
    )
    has_compact_volume = re.search(r"\b[1-8][0-9]-[0-9]{1,2}l\b", lower_value)
    has_compact_dimensions = bool(parse_compact_dimension_slug(lower_value))

    return bool(
        has_length
        or has_compact_length
        or has_volume
        or has_compact_volume
        or has_compact_dimensions
    )


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

        if looks_like_slug_variant(value) and not looks_like_dimension_variant(value):
            continue

        if not looks_like_dimension_variant(value):
            continue

        options.append(value)

    return sorted(set(options))


def is_excluded_url(url):
    lower_url = url.lower()

    return any(part in lower_url for part in EXCLUDED_SLUG_PARTS)


def row_quality(row):
    score = 0

    if row.get("stock_quantity") is not None:
        score += 5

    if row.get("volume_litres") is not None:
        score += 4

    if row.get("length"):
        score += 3

    if row.get("width"):
        score += 2

    if row.get("thickness"):
        score += 2

    if row.get("image_url"):
        score += 2

    if row.get("price"):
        score += 1

    if row.get("variant_source") == "woocommerce_variation_json":
        score += 3

    return score


def dedupe_rows(rows):
    best_rows = {}

    for row in rows:
        key = (
            row.get("product_url"),
            row.get("title"),
            row.get("length"),
            str(row.get("volume_litres") or ""),
            str(row.get("stock_quantity") or ""),
        )

        if key not in best_rows:
            best_rows[key] = row
            continue

        if row_quality(row) > row_quality(best_rows[key]):
            best_rows[key] = row

    return list(best_rows.values())


def build_base_item(url, response, soup, html_text):
    title = extract_title(soup)
    price = extract_price_from_page(soup, html_text)
    availability_text = extract_availability_text(soup)
    images = extract_product_images(soup, title)
    image_url = images[0] if images else None

    return {
        "retailer": RETAILER_NAME,
        "retailer_url": BASE_URL,
        "website": BASE_URL,
        "product_url": url,
        "available": response.status_code == 200,
        "source": "coopers_product_sitemap",
        "status_code": response.status_code,
        "title": title,
        "price": price,
        "availability_text": availability_text,
        "image_url": image_url,
        "product_image_url": image_url,
        "images": images,
    }


def rows_from_woocommerce_variations(base_item, variations):
    rows = []

    for variation in variations:
        if not is_in_stock(variation):
            continue

        attribute_text = variation_attribute_text(variation)
        availability_html = variation.get("availability_html") or ""

        variation_text = " | ".join(
            [
                value
                for value in [
                    attribute_text,
                    str(variation.get("sku") or ""),
                    availability_html,
                ]
                if value
            ]
        )

        if not looks_like_dimension_variant(variation_text):
            continue

        parsed_dimensions = parse_dimension_values(variation_text)
        variation_image_url = extract_variation_image(variation)

        price = normalise_price(
            variation.get("display_price")
            or variation.get("display_regular_price")
            or base_item.get("price")
        )

        image_candidates = []
        if variation_image_url:
            image_candidates.append(variation_image_url)

        image_candidates.extend(base_item.get("images") or [])
        ranked_images = rank_images(image_candidates, base_item.get("title"))
        image_url = ranked_images[0] if ranked_images else None

        row = dict(base_item)
        row["variant"] = variation_text
        row["variant_source"] = "woocommerce_variation_json"
        row["variation_id"] = variation.get("variation_id")
        row["sku"] = variation.get("sku")
        row["available"] = True
        row["price"] = price
        row["image_url"] = image_url
        row["product_image_url"] = image_url
        row["images"] = ranked_images
        row["length"] = parsed_dimensions.get("length") or extract_length(variation_text)
        row["width"] = parsed_dimensions.get("width") or extract_width(variation_text)
        row["thickness"] = parsed_dimensions.get("thickness") or extract_thickness(variation_text)
        row["volume_litres"] = (
            parsed_dimensions.get("volume_litres")
            if parsed_dimensions.get("volume_litres") is not None
            else extract_volume_litres(variation_text)
        )
        row["stock_quantity"] = extract_stock_quantity(availability_html)
        rows.append(row)

    return rows


def rows_from_dropdown_options(base_item, soup):
    rows = []

    for option in extract_variant_options(soup):
        parsed_dimensions = parse_dimension_values(option)

        row = dict(base_item)
        row["variant"] = option
        row["variant_source"] = "dropdown_option"
        row["length"] = parsed_dimensions.get("length") or extract_length(option)
        row["width"] = parsed_dimensions.get("width") or extract_width(option)
        row["thickness"] = parsed_dimensions.get("thickness") or extract_thickness(option)
        row["volume_litres"] = (
            parsed_dimensions.get("volume_litres")
            if parsed_dimensions.get("volume_litres") is not None
            else extract_volume_litres(option)
        )
        row["stock_quantity"] = None
        rows.append(row)

    return rows


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

        if response.status_code != 200:
            return [
                {
                    "retailer": RETAILER_NAME,
                    "retailer_url": BASE_URL,
                    "website": BASE_URL,
                    "product_url": url,
                    "available": False,
                    "source": "coopers_product_sitemap",
                    "status_code": response.status_code,
                }
            ]

        html_text = response.text
        soup = BeautifulSoup(html_text, "html.parser")
        base_item = build_base_item(url, response, soup, html_text)

        variations = extract_variation_json(soup)
        variation_rows = rows_from_woocommerce_variations(base_item, variations)

        if variation_rows:
            return dedupe_rows(variation_rows)

        dropdown_rows = rows_from_dropdown_options(base_item, soup)

        if dropdown_rows:
            return dedupe_rows(dropdown_rows)

        return [base_item]

    except Exception as error:
        return [
            {
                "retailer": RETAILER_NAME,
                "retailer_url": BASE_URL,
                "website": BASE_URL,
                "product_url": url,
                "available": False,
                "source": "coopers_product_sitemap",
                "error": str(error),
            }
        ]


def write_output(results, output_file):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def print_summary(results, output_file):
    variant_rows = sum(1 for item in results if item.get("variant"))
    length_rows = sum(1 for item in results if item.get("length"))
    volume_rows = sum(1 for item in results if item.get("volume_litres"))
    stock_rows = sum(1 for item in results if item.get("stock_quantity") is not None)
    image_rows = sum(1 for item in results if item.get("image_url"))

    print("", flush=True)
    print(f"Inventory rows collected: {len(results)}", flush=True)
    print(f"Variant rows collected: {variant_rows}", flush=True)
    print(f"Rows with length: {length_rows}", flush=True)
    print(f"Rows with volume: {volume_rows}", flush=True)
    print(f"Rows with stock quantity: {stock_rows}", flush=True)
    print(f"Rows with image: {image_rows}", flush=True)
    print(f"Output file: {output_file}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run against selected Coopers problem pages only.",
    )
    parser.add_argument(
        "--debug-url",
        help="Run against one product URL and write to a debug output file.",
    )

    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("Coopers Board Store inventory scrape", flush=True)
    print("=" * 60, flush=True)

    output_file = OUTPUT_FILE

    if args.debug_url:
        print("Mode: debug-url", flush=True)
        product_urls = [args.debug_url]
        output_file = OUTPUT_DIR / "coopers_debug_inventory.json"
    elif args.test:
        print("Mode: test", flush=True)
        product_urls = TEST_PRODUCT_URLS
        output_file = OUTPUT_DIR / "coopers_test_inventory.json"
    else:
        print("Mode: full", flush=True)
        product_urls = get_product_urls()

    print(f"Product URLs found: {len(product_urls)}", flush=True)

    results = []

    for index, url in enumerate(product_urls, start=1):
        print(f"[{index}/{len(product_urls)}] {url}", flush=True)

        items = extract_product_data(url)
        results.extend(items)

        time.sleep(0.5)

    results = dedupe_rows(results)

    write_output(results, output_file)
    print_summary(results, output_file)

    if args.debug_url:
        print("", flush=True)
        print("Debug rows:", flush=True)

        for item in results[:80]:
            print(
                json.dumps(
                    {
                        "title": item.get("title"),
                        "variant": item.get("variant"),
                        "variant_source": item.get("variant_source"),
                        "length": item.get("length"),
                        "width": item.get("width"),
                        "thickness": item.get("thickness"),
                        "volume_litres": item.get("volume_litres"),
                        "stock_quantity": item.get("stock_quantity"),
                        "price": item.get("price"),
                        "image_url": item.get("image_url"),
                        "product_url": item.get("product_url"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()