from __future__ import annotations

import json
import re
from html import unescape
from urllib.parse import urldefrag, urljoin


BOARD_TERMS = [
    "surfboard",
    "surf board",
    "shortboard",
    "longboard",
    "mid length",
    "midlength",
    "mid-length",
    "fish",
    "twin fin",
    "twinfin",
    "thruster",
    "funboard",
    "mini mal",
    "malibu",
    "foamie",
    "softboard",
]

BOARD_BRANDS = [
    "al merrick",
    "aloha",
    "bradley",
    "channel islands",
    "christenson",
    "ci",
    "ci surfboards",
    "dhd",
    "firewire",
    "hayden shapes",
    "haydenshapes",
    "indio",
    "js",
    "js industries",
    "lib tech",
    "lost",
    "mayhem",
    "norden",
    "nsp",
    "pukas",
    "pyzel",
    "rusty",
    "sharpeye",
    "sharp eye",
    "slater designs",
    "torq",
]

EXCLUDE_TERMS = [
    "bag",
    "bodyboard",
    "boardbag",
    "clothing",
    "deck grip",
    "fins",
    "grip",
    "leash",
    "pad",
    "skateboard",
    "surfskate",
    "snowboard",
    "soft rack",
    "traction",
    "wax",
    "wetsuit",
]

PRICE_RE = re.compile(r"(?:€|eur\s*)\s*([0-9]+(?:[.,][0-9]{2})?)|([0-9]+(?:[.,][0-9]{2})?)\s*(?:€|eur)", re.I)
JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
TAG_RE = re.compile(r"<[^>]+>")


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def lower(value: object) -> str:
    return clean(value).lower()


def parse_price(value: object) -> str:
    text = clean(value)
    if not text:
        return ""

    match = PRICE_RE.search(text)
    if not match:
        return ""

    amount = next(group for group in match.groups() if group)
    return amount.replace(".", "").replace(",", ".") if "," in amount and "." in amount else amount.replace(",", ".")


def contains_phrase(text: str, phrases: list[str]) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) for phrase in phrases)


def classify_product(title: str, url: str = "", extra_text: str = "") -> dict:
    text = lower(" ".join([title, url, extra_text]))
    confidence = 0
    reasons = []

    if contains_phrase(text, EXCLUDE_TERMS):
        return {
            "accepted": False,
            "parseConfidence": 0,
            "filterReasons": ["excluded_product_type"],
        }

    if contains_phrase(text, BOARD_TERMS):
        confidence += 5
        reasons.append("board_term")

    if contains_phrase(text, BOARD_BRANDS):
        confidence += 2
        reasons.append("known_board_brand")

    if re.search(r"\b[5-9]\s*(?:'|ft|’)\s*\d{0,2}", text):
        confidence += 3
        reasons.append("length_signal")

    accepted = confidence >= 5
    if not accepted:
        reasons.append("low_confidence_or_missing_board_identity")

    return {
        "accepted": accepted,
        "parseConfidence": confidence,
        "filterReasons": reasons,
    }


def strip_tags(value: str) -> str:
    return clean(TAG_RE.sub(" ", value))


def is_option_only_title(title: str) -> bool:
    text = lower(title)
    without_lengths = re.sub(r"\b[4-9]\s*(?:'|ft|’)\s*\d{0,2}(?:''|\"|”)?", " ", text)
    without_sizes = re.sub(r"\b(?:xs|s|m|l|xl|xxl|one size)\b", " ", without_lengths)
    return bool(text) and not re.search(r"[a-z]{3,}", without_sizes)


def find_json_ld_objects(html: str) -> list[object]:
    objects = []

    for match in JSON_LD_RE.finditer(html):
        raw = clean(match.group(1))
        if not raw:
            continue

        try:
            objects.append(json.loads(raw))
        except json.JSONDecodeError:
            continue

    return objects


def walk_json(value: object) -> list[dict]:
    found = []

    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(walk_json(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk_json(child))

    return found


def first_text(value: object) -> str:
    if isinstance(value, list):
        for item in value:
            text = first_text(item)
            if text:
                return text
        return ""

    if isinstance(value, dict):
        return clean(value.get("name") or value.get("url") or "")

    return clean(value)


def product_rows_from_json_ld(html: str, source_url: str) -> list[dict]:
    rows = []

    for root in find_json_ld_objects(html):
        for item in walk_json(root):
            item_type = lower(item.get("@type"))
            if item_type not in {"product", "listitem"}:
                continue

            product = item.get("item") if isinstance(item.get("item"), dict) else item
            title = first_text(product.get("name"))
            url = first_text(product.get("url"))

            if not title and not url:
                continue

            offers = product.get("offers") if isinstance(product, dict) else {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if not isinstance(offers, dict):
                offers = {}

            brand = product.get("brand") if isinstance(product, dict) else ""
            image = first_text(product.get("image")) if isinstance(product, dict) else ""
            availability = lower(offers.get("availability"))

            rows.append({
                "productTitle": title,
                "productUrl": urljoin(source_url, url),
                "productImageUrl": urljoin(source_url, image) if image else "",
                "brand": first_text(brand),
                "vendor": first_text(brand),
                "priceAmount": clean(offers.get("price") or parse_price(json.dumps(offers))),
                "isAvailable": True if "instock" in availability else False if "outofstock" in availability else None,
                "stockStatus": "in_stock" if "instock" in availability else "out_of_stock" if "outofstock" in availability else "",
                "sku": clean(product.get("sku") if isinstance(product, dict) else ""),
                "sourceSnippet": title,
                "sourceUrl": source_url,
            })

    return dedupe_rows(rows)


def product_rows_from_prestashop_cards(html: str, source_url: str) -> list[dict]:
    rows = []
    html = html.replace('\\"', '"').replace("\\/", "/").replace("\\n", " ").replace("\\t", " ").replace("\\u20ac", "€")
    title_re = re.compile(
        r'class=["\'][^"\']*product-title[^"\']*["\'][^>]*>\s*<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.I | re.S,
    )

    for title_match in title_re.finditer(html):
        start = max(0, title_match.start() - 3000)
        end = min(len(html), title_match.end() + 2500)
        card = html[start:end]

        title = strip_tags(title_match.group(2))
        product_url = urljoin(source_url, clean(title_match.group(1)))
        brand_match = re.search(
            r'class=["\'][^"\']*product-brand[^"\']*["\'][^>]*>.*?<a[^>]*>(.*?)</a>',
            card,
            re.I | re.S,
        )
        price_content_match = re.search(
            r'class=["\'][^"\']*product-price[^"\']*["\'][^>]*content=["\']([^"\']+)["\']',
            card,
            re.I | re.S,
        )
        price_text_match = re.search(
            r'class=["\'][^"\']*product-price[^"\']*["\'][^>]*>(.*?)</span>',
            card,
            re.I | re.S,
        )
        image_match = re.search(
            r'<img[^>]+(?:data-full-size-image-url|data-src|src)=["\']([^"\']+)["\']',
            card,
            re.I,
        )
        stock_text = lower(card)

        rows.append({
            "productTitle": title,
            "productUrl": product_url,
            "productImageUrl": urljoin(source_url, clean(image_match.group(1))) if image_match else "",
            "brand": strip_tags(brand_match.group(1)) if brand_match else "",
            "vendor": strip_tags(brand_match.group(1)) if brand_match else "",
            "priceAmount": clean(price_content_match.group(1)) if price_content_match else parse_price(price_text_match.group(1) if price_text_match else ""),
            "isAvailable": True if "in stock" in stock_text or "product-available" in stock_text else False if "out of stock" in stock_text or "product-unavailable" in stock_text else None,
            "stockStatus": "in_stock" if "in stock" in stock_text or "product-available" in stock_text else "out_of_stock" if "out of stock" in stock_text or "product-unavailable" in stock_text else "",
            "sku": "",
            "sourceSnippet": strip_tags(card)[:500],
            "sourceUrl": source_url,
        })

    return dedupe_rows(rows)


def product_rows_from_prestashop_json(html: str, source_url: str) -> list[dict]:
    text = clean(html)
    if not text.startswith("{"):
        return []

    try:
        data = json.loads(html)
    except json.JSONDecodeError:
        return []

    products = data.get("products")
    if not isinstance(products, list):
        return []

    rows = []

    for product in products:
        if not isinstance(product, dict):
            continue

        image = product_image_from_prestashop_json(product)
        quantity = product.get("quantity")
        availability = lower(product.get("availability"))
        available = None
        if isinstance(quantity, int):
            available = quantity > 0
        elif availability:
            available = "available" in availability and "unavailable" not in availability

        attributes = product.get("attributes") if isinstance(product.get("attributes"), dict) else {}
        attribute_text = " ".join(
            clean(attribute.get("name"))
            for attribute in attributes.values()
            if isinstance(attribute, dict)
        )

        rows.append({
            "productTitle": clean(product.get("name")),
            "productUrl": clean(product.get("canonical_url") or product.get("url")),
            "productImageUrl": image,
            "brand": clean(product.get("manufacturer_name") or product.get("manufacturer")),
            "vendor": clean(product.get("manufacturer_name") or product.get("manufacturer")),
            "priceAmount": clean(product.get("price_amount") or parse_price(product.get("price") or product.get("regular_price"))),
            "isAvailable": available,
            "stockStatus": "in_stock" if available is True else "out_of_stock" if available is False else "",
            "sku": clean(product.get("reference") or product.get("ean13") or product.get("id")),
            "sourceSnippet": clean(" ".join([product.get("name", ""), attribute_text]))[:500],
            "sourceUrl": source_url,
        })

    return dedupe_rows(rows)


def product_image_from_prestashop_json(product: dict) -> str:
    cover = product.get("cover") if isinstance(product.get("cover"), dict) else {}
    by_size = cover.get("bySize") if isinstance(cover.get("bySize"), dict) else {}

    for size_name in ["large_default", "home_default", "medium_default", "cart_default", "small_default"]:
        image = by_size.get(size_name)
        if isinstance(image, dict) and image.get("url"):
            return clean(image["url"])

    if cover.get("url"):
        return clean(cover["url"])

    images = product.get("images")
    if isinstance(images, list) and images:
        candidate = {"cover": images[0]}
        return product_image_from_prestashop_json(candidate)

    return ""


def product_rows_from_woocommerce_cards(html: str, source_url: str) -> list[dict]:
    rows = []
    card_re = re.compile(
        r'<div\b[^>]*class=["\'][^"\']*product-small[^"\']*["\'][^>]*>.*?(?=<div\b[^>]*class=["\'][^"\']*product-small|\Z)',
        re.I | re.S,
    )

    for match in card_re.finditer(html):
        card = match.group(0)
        title_match = re.search(
            r'class=["\'][^"\']*woocommerce-loop-product__link[^"\']*["\'][^>]*>(.*?)</a>',
            card,
            re.I | re.S,
        )
        link_match = re.search(r'<a\b[^>]*href=["\']([^"\']+/product/[^"\']+)["\']', card, re.I)
        if not title_match or not link_match:
            continue

        image_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', card, re.I)
        sku_match = re.search(r'data-product_sku=["\']([^"\']+)["\']', card, re.I)
        stock_text = lower(card)
        is_available = False if "outofstock" in stock_text or "out of stock" in stock_text else True

        rows.append({
            "productTitle": strip_tags(title_match.group(1).replace("</br>", " ")),
            "productUrl": urljoin(source_url, clean(link_match.group(1))),
            "productImageUrl": urljoin(source_url, clean(image_match.group(1))) if image_match else "",
            "brand": "",
            "vendor": "",
            "priceAmount": parse_price(strip_tags(card)),
            "isAvailable": is_available,
            "stockStatus": "in_stock" if is_available else "out_of_stock",
            "sku": clean(sku_match.group(1)) if sku_match else "",
            "sourceSnippet": strip_tags(card)[:500],
            "sourceUrl": source_url,
        })

    return dedupe_rows(rows)


def product_rows_from_daisuke_cards(html: str, source_url: str) -> list[dict]:
    """Parse Surf Corner's Daisuke listing cards without accepting nav links."""
    rows = []
    card_re = re.compile(
        r'<div\b[^>]*class=["\'][^"\']*prod-cont[^"\']*["\'][^>]*>.*?(?=<div\b[^>]*class=["\'][^"\']*prod-cont|\Z)',
        re.I | re.S,
    )
    for match in card_re.finditer(html):
        card = match.group(0)
        link = re.search(
            r'<div\b[^>]*class=["\'][^"\']*prod-title[^"\']*["\'][^>]*>\s*<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            card,
            re.I | re.S,
        )
        if not link:
            continue
        brand = re.search(
            r'<div\b[^>]*class=["\'][^"\']*brand[^"\']*["\'][^>]*>.*?<a[^>]*>(.*?)</a>',
            card,
            re.I | re.S,
        )
        image = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', card, re.I)
        quantity = re.search(r'data-tagmanager-quantity=["\'](\d+)["\']', card, re.I)
        product_id = re.search(r'data-tagmanager-id=["\']([^"\']+)["\']', card, re.I)
        available = int(quantity.group(1)) > 0 if quantity else None
        rows.append({
            "productTitle": strip_tags(link.group(2)),
            "productUrl": urljoin(source_url, clean(link.group(1))),
            "productImageUrl": urljoin(source_url, clean(image.group(1))) if image else "",
            "brand": strip_tags(brand.group(1)) if brand else "",
            "vendor": strip_tags(brand.group(1)) if brand else "",
            "priceAmount": parse_price(strip_tags(card)),
            "isAvailable": available,
            "stockStatus": "in_stock" if available is True else "out_of_stock" if available is False else "",
            "sku": clean(product_id.group(1)) if product_id else "",
            "sourceSnippet": strip_tags(card)[:1000],
            "sourceUrl": source_url,
        })
    return dedupe_rows(rows)


def product_rows_from_links(html: str, source_url: str, product_path_markers: list[str]) -> list[dict]:
    rows = []
    html = html.replace('\\"', '"').replace("\\/", "/").replace("\\n", " ").replace("\\t", " ")
    anchor_re = re.compile(r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    action_labels = {
        "add to cart",
        "buy now",
        "choose options",
        "read more",
        "select options",
        "view product",
    }
    category_labels = {
        "fish surfboards",
        "funboards",
        "longboard",
        "longboards",
        "mid-length surfboards",
        "shortboards",
        "softboards",
        "softtops",
        "surfboards",
        "surfboards back",
    }

    for match in anchor_re.finditer(html):
        href = clean(match.group(1))
        body = match.group(2)

        if not any(marker in href.lower() for marker in product_path_markers):
            continue

        title = strip_tags(body)
        title_lower = lower(title)
        if (
            len(title) < 3
            or title_lower in action_labels
            or title_lower in BOARD_BRANDS
            or title_lower in category_labels
            or title_lower.endswith(" back")
            or re.fullmatch(r"[a-z0-9& -]+ surfboards", title_lower) is not None
            or title_lower.startswith("shop ")
            or is_option_only_title(title)
        ):
            continue

        snippet_start = max(0, match.start() - 2200)
        snippet_end = min(len(html), match.end() + 1200)
        snippet = html[snippet_start:snippet_end]

        img_match = re.search(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']', snippet, re.I)
        srcset_match = re.search(r'(https?://[^"\']+\.(?:jpg|jpeg|png|webp))\s+\d+w', snippet, re.I)
        price = parse_price(strip_tags(snippet))
        availability_text = lower(snippet)
        is_available = True if " instock " in f" {availability_text} " else False if "outofstock" in availability_text or "out of stock" in availability_text else None

        rows.append({
            "productTitle": title,
            "productUrl": urljoin(source_url, href),
            "productImageUrl": urljoin(source_url, clean(img_match.group(1))) if img_match else clean(srcset_match.group(1)) if srcset_match else "",
            "brand": "",
            "vendor": "",
            "priceAmount": price,
            "isAvailable": is_available,
            "stockStatus": "in_stock" if is_available is True else "out_of_stock" if is_available is False else "",
            "sku": "",
            "sourceSnippet": strip_tags(snippet)[:500],
            "sourceUrl": source_url,
        })

    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict]) -> list[dict]:
    by_key = {}

    for row in rows:
        url = lower(urldefrag(clean(row.get("productUrl")))[0]).rstrip("/")
        source_url = lower(urldefrag(clean(row.get("sourceUrl")))[0]).rstrip("/")
        title = lower(row.get("productTitle"))
        key = (url, title) if source_url and url == source_url else (url or title)
        if not key:
            continue

        current = by_key.get(key)
        if current is None or row_quality(row) > row_quality(current):
            by_key[key] = row

    return list(by_key.values())


def row_quality(row: dict) -> int:
    title = clean(row.get("productTitle"))
    text = lower(" ".join([title, row.get("productUrl", ""), row.get("sourceSnippet", "")]))
    score = len(title.split())

    if contains_phrase(lower(title), BOARD_TERMS):
        score += 20
    if contains_phrase(text, BOARD_BRANDS):
        score += 4
    if row.get("priceAmount"):
        score += 3
    if row.get("productImageUrl"):
        score += 2

    return score


def decorate_rows(rows: list[dict], target: dict, source_url: str) -> tuple[list[dict], int]:
    accepted = []
    rejected = 0

    for row in rows:
        score = classify_product(
            row.get("productTitle", ""),
            row.get("productUrl", ""),
            row.get("sourceSnippet", ""),
        )

        if score["accepted"]:
            accepted.append({
                "retailerSlug": target["retailerSlug"],
                "retailerName": target["retailerName"],
                "regionCode": target["regionCode"],
                "country": target["country"],
                "platform": target["platform"],
                "sourceUrl": source_url,
                "productTitle": clean(row.get("productTitle")),
                "productUrl": clean(row.get("productUrl")),
                "productImageUrl": clean(row.get("productImageUrl")),
                "brand": clean(row.get("brand")),
                "vendor": clean(row.get("vendor")),
                "priceAmount": clean(row.get("priceAmount")),
                "priceCurrency": target.get("priceCurrency", "EUR"),
                "isAvailable": row.get("isAvailable"),
                "stockStatus": clean(row.get("stockStatus")),
                "sku": clean(row.get("sku")),
                "sourceSnippet": clean(row.get("sourceSnippet"))[:500],
                "parseConfidence": score["parseConfidence"],
                "discoveryStatus": "accepted",
                "filterReasons": score["filterReasons"],
            })
        else:
            rejected += 1

    return accepted, rejected
