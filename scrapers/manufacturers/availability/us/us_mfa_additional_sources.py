from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests


REGION_CODE = "US"
SOURCE = "manufacturer_direct"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Quivrr-US-MFA/1.2; "
        "+https://quivrr.app/united-states)"
    )
}
OUTPUT_ROOT = Path("scrapers/manufacturers/availability")

EXTRA_TARGETS = {
    "christenson": {
        "brand_name": "Christenson",
        "source_url": "https://christensonsurfboards.com/surfboard-stock",
        "parser": "christenson",
    },
    "misfit": {
        "brand_name": "Misfit Shapes",
        "source_url": "https://misfitshapes.com/collections/current-models/products.json",
        "parser": "misfit",
    },
    "chilli": {
        "brand_name": "Chilli",
        "source_url": "https://www.chillisurfboards.com/shop/surfboards/?region=usa&direct=1",
        "parser": "chilli",
    },
    "pukas": {
        "brand_name": "Pukas",
        "source_url": "https://pukassurfshop.com/collections/pukas-surfboards/products.json",
        "parser": "pukas",
    },
}

LOST_US_BASE_URL = "https://lostsurfboards.net"
LOST_US_CATEGORY_URL = "https://lostsurfboards.net/product-category/surfboards/"
LOST_US_PRODUCT_CAT_API = "https://lostsurfboards.net/wp-json/wp/v2/product_cat?slug=surfboards"
LOST_US_STORE_API_CANDIDATES = (
    "https://lostsurfboards.net/wp-json/wc/store/v1/products",
    "https://lostsurfboards.net/wp-json/wc/store/products",
)
LOST_US_REQUEST_FAILURE_REASON = "geo_blocked_requires_us_egress"
LOST_SURFBOARD_KEYWORDS = (
    "surfboard",
    "driver",
    "sub driver",
    "rocket",
    "puddle",
    "party platter",
    "sabotaj",
    "uber",
    "quiver killer",
    "step driver",
    "speed demon",
    "rnf",
    "rad ripper",
    "crowd killer",
    "evil twin",
    "swordfish",
    "california twin",
    "3.0",
)
LOST_REJECT_KEYWORDS = (
    "fin",
    "fins",
    "traction",
    "deck grip",
    "tail pad",
    "pad",
    "leash",
    "cover",
    "bag",
    "wax",
    "tee",
    "shirt",
    "hat",
    "cap",
    "beanie",
    "towel",
    "sticker",
    "gift card",
    "plug",
)
FRACTION_MAP = {
    "1/16": 0.0625,
    "1/8": 0.125,
    "3/16": 0.1875,
    "1/4": 0.25,
    "5/16": 0.3125,
    "3/8": 0.375,
    "7/16": 0.4375,
    "1/2": 0.5,
    "9/16": 0.5625,
    "5/8": 0.625,
    "11/16": 0.6875,
    "3/4": 0.75,
    "13/16": 0.8125,
    "7/8": 0.875,
    "15/16": 0.9375,
}

MISFIT_PRODUCTS_URL = "https://misfitshapes.com/collections/current-models/products.json"
MISFIT_SOURCE_STOREFRONT = "https://misfitshapes.com"
MISFIT_CATALOGUE_PATH = Path(
    "scrapers/brands/misfit/output/misfit_master_catalogue_clean.json"
)
MISFIT_PRODUCT_CURRENCY = "AUD"

PUKAS_PRODUCTS_URL = "https://pukassurfshop.com/collections/pukas-surfboards/products.json"
PUKAS_SOURCE_STOREFRONT = "https://pukassurfshop.com"
PUKAS_PRODUCT_CURRENCY = "EUR"
PUKAS_TITLE_RE = re.compile(
    r"^Pukas Surfboards\s*-\s*(?P<model>.+?)\s+by\s+.+?\s*-\s*"
    r"(?P<length>[4-9]'\d{1,2})\"?\s*x\s*"
    r"(?P<width>\d+(?:\.\d+)?)\"?\s*x\s*"
    r"(?P<thickness>\d+(?:\.\d+)?)\"?\s*-\s*"
    r"(?P<volume>\d+(?:\.\d+)?)L(?:\s*-\s*(?P<source_code>[A-Z0-9]+))?$",
    re.I,
)

CHRISTENSON_STOCK_URL = "https://christensonsurfboards.com/surfboard-stock"
CHRISTENSON_PRODUCT_BLOCK_RE = re.compile(
    r'<a\s+href="(?P<href>/surfboard-stock/[^"]+)"[^>]*class="product\b[^"]*"[^>]*>(?P<body>.*?)</a>',
    re.I | re.S,
)
CHRISTENSON_IMAGE_RE = re.compile(r'<img[^>]+data-image="(?P<image>[^"]+)"', re.I)
CHRISTENSON_PRODUCT_TITLE_RE = re.compile(
    r'<div class="product-title">(?P<title>[^<]+)</div>',
    re.I,
)
CHRISTENSON_PRODUCT_PRICE_RE = re.compile(
    r'<div class="product-price">\s*(?P<price>\$[\d,]+(?:\.\d{2})?)\s*</div>',
    re.I,
)
CHRISTENSON_DETAIL_RE = re.compile(
    r'<meta\s+property="og:description"\s+content="(?P<description>[^"]+)"',
    re.I,
)
CHRISTENSON_PRICE_RE = re.compile(
    r'<meta\s+property="product:price:amount"\s+content="(?P<price>[\d.]+)"',
    re.I,
)
CHRISTENSON_TITLE_RE = re.compile(r"<title>(?P<title>[^<]+)</title>", re.I)
CHRISTENSON_BASE_SPECS_RE = re.compile(
    r"(?P<length>[4-9]['’]\d{1,2})\s*[x×]\s*"
    r"(?P<width>\d+(?:\s+\d+/\d+)?)\s*x\s*"
    r"(?P<thickness>\d+(?:\s+\d+/\d+)?)\s*-\s*"
    r"(?P<volume>\d+(?:\.\d+)?)L",
    re.I,
)
CHRISTENSON_FIN_RE = re.compile(
    r"(?P<fin_count>\d+)\s*x\s*(?P<fin_system>FCS ?II|FCS2|Futures|Future|Single)",
    re.I,
)

CHILLI_MODELS_URL = "https://chilli.shaperbuddy.com/api/v1/surfboardmodels"
CHILLI_DETAIL_URL = "https://chilli.shaperbuddy.com/api/v1/surfboardmodels/{id}?lang=en"
CHILLI_STOREFRONT_URL = "https://www.chillisurfboards.com/shop/surfboards/?region=usa&direct=1"
CHILLI_STOREFRONT_MODEL_RE = re.compile(
    r'href="(?P<href>/surfboards/detail\.php\?id=(?P<model_id>\d+)&direct=1&region=usa)"'
    r'[^>]*data-boardimg="(?P<image>[^"]+)"'
    r'[^>]*data-min_price="(?P<price>\d+(?:\.\d+)?)"'
    r'[^>]*data-currencyiso="(?P<currency>[A-Z]{3})"'
    r'[^>]*data-currencysymbol="[^"]*"'
    r'[^>]*data-model="(?P<model>[^"]+)"',
    re.I,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean(value: object) -> str:
    text = str(value or "")
    for _ in range(2):
        text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("×", "x")
    text = (
        text.replace("¼", " 1/4")
        .replace("½", " 1/2")
        .replace("¾", " 3/4")
        .replace("⅛", " 1/8")
        .replace("⅜", " 3/8")
        .replace("⅝", " 5/8")
        .replace("⅞", " 7/8")
    )
    return re.sub(r"\s+", " ", text).strip()


def normalise_key(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalise_length(value: object) -> str | None:
    text = clean(value).replace('"', "")
    match = re.search(r"([4-9])\s*'\s*(\d{1,2})", text)
    if not match:
        return None
    return f"{match.group(1)}'{int(match.group(2))}"


def normalise_dimension_text(value: object) -> str | None:
    text = clean(value).replace('"', "")
    return text or None


def normalise_fin_system(value: object) -> str | None:
    text = clean(value).lower()
    if "fcs ii" in text or "fcsii" in text or "fcs2" in text or "fcs 2" in text:
        return "FCS II"
    if "future" in text:
        return "Futures"
    if "single" in text:
        return "Single"
    if "2+1" in text:
        return "2+1"
    return clean(value) or None


def normalise_construction(value: object) -> str | None:
    text = clean(value).lower()
    if "futureflex" in text or "future flex" in text:
        return "FutureFlex"
    if "eps" in text or "epoxy" in text:
        return "EPS"
    if "pu" in text or "poly" in text or "stringer" in text:
        return "PU"
    return clean(value) or None


class SourceGeoBlockedError(RuntimeError):
    """Raised when a source can only be reached from a specific egress region."""


def decimal_inches(value: object) -> str | None:
    text = clean(value).replace('"', "")
    if not text:
        return None
    try:
        return f"{float(text):.2f}"
    except (TypeError, ValueError):
        pass
    total = 0.0
    for part in text.split():
        if part in FRACTION_MAP:
            total += FRACTION_MAP[part]
            continue
        try:
            total += float(part)
        except (TypeError, ValueError):
            return text or None
    return f"{total:.2f}"


def lost_is_available(product: dict) -> bool:
    if product.get("is_in_stock") is True:
        return True
    if product.get("stock_status") == "instock":
        return True
    return False


def lost_price_amount(product: dict) -> float | None:
    prices = product.get("prices") or {}
    raw_price = prices.get("price")
    if raw_price in (None, ""):
        return None
    try:
        minor_units = int(prices.get("currency_minor_unit", 2))
    except (TypeError, ValueError):
        minor_units = 2
    try:
        return round(float(raw_price) / (10**minor_units), minor_units)
    except (TypeError, ValueError):
        return None


def lost_price_currency(product: dict) -> str | None:
    prices = product.get("prices") or {}
    return clean(prices.get("currency_code")) or "USD"


def lost_image_url(product: dict) -> str | None:
    images = product.get("images") or []
    for image in images:
        if not isinstance(image, dict):
            continue
        source = clean(image.get("src") or image.get("thumbnail") or image.get("srcset"))
        if source:
            return source
    return None


def looks_like_lost_surfboard(product: dict) -> bool:
    combined = " ".join(
        clean(value).lower()
        for value in (
            product.get("name"),
            product.get("slug"),
            product.get("short_description"),
            product.get("description"),
        )
        if clean(value)
    )
    if any(word in combined for word in LOST_REJECT_KEYWORDS):
        return False
    if any(word in combined for word in LOST_SURFBOARD_KEYWORDS):
        return True
    return bool(parse_lost_dimensions(combined)[0])


def normalise_lost_model_name(product_name: object) -> str | None:
    title = clean(product_name)
    original_title = title
    for suffix in (
        "Black Sheep",
        "Light Speed II",
        "LightSpeed II",
        "Light Speed",
        "LightSpeed",
        "Lib Tech",
        "Carbon Wrap",
        "C4",
        "PU",
    ):
        title = re.sub(rf"\b{re.escape(suffix)}\b", "", title, flags=re.I)
    title = re.sub(r"\([^)]*\)", "", title)
    title = re.sub(r"\bwith spray\b", "", title, flags=re.I)
    title = re.sub(r"\bsurfboard\b", "", title, flags=re.I)
    title = re.sub(
        r"\b[4-9]'\d{1,2}\b.*$",
        "",
        title,
        flags=re.I,
    )
    title = re.sub(r"\s+", " ", title).strip(" -|")
    aliases = {
        "The Original Puddle Jumper": "Original Puddle Jumper '25",
        "Mini Driver": "Mini Driver (Re Issue)",
        "Formula 1 Round Pin": "Formula 1 Round",
        "Formula 1 x Yago Dora": "Formula 1 Round",
        "RNF Twinzer '96er": "RNF Twinzer+ '96er",
        "RNF '96": "RNF 96",
        "The Ripper": "The Ripper Squash",
        "RNF 96er": "RNF 96",
        "Driver 3.0 Grom": "Driver 3.0 Squash",
    }
    if title in aliases:
        return aliases[title]
    return title or original_title or None


def parse_lost_dimensions(text: object) -> tuple[str | None, str | None, str | None, float | None]:
    value = clean(text).replace("?", "").replace('"', "")
    if not value:
        return None, None, None, None
    volume = None
    volume_match = re.search(r"(\d{1,2}(?:\.\d+)?)\s*l\b", value, re.I)
    if volume_match:
        try:
            volume = float(volume_match.group(1))
        except (TypeError, ValueError):
            volume = None
    exact_match = re.search(
        r"(?P<length>\d+'\d+)\s+"
        r"(?P<width>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)\s+"
        r"(?P<thickness>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)\s+"
        r"(?P<volume>\d{1,2}(?:\.\d+)?)\s*l\b",
        value,
        re.I,
    )
    if exact_match:
        return (
            clean(exact_match.group("length")),
            decimal_inches(exact_match.group("width")),
            decimal_inches(exact_match.group("thickness")),
            float(exact_match.group("volume")),
        )
    separator_match = re.search(
        r"(?P<length>\d+'\d+)\s*(?:x|X|/|\|)\s*"
        r"(?P<width>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)\s*(?:x|X|/|\|)\s*"
        r"(?P<thickness>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)",
        value,
        re.I,
    )
    if separator_match:
        return (
            clean(separator_match.group("length")),
            decimal_inches(separator_match.group("width")),
            decimal_inches(separator_match.group("thickness")),
            volume,
        )
    length_match = re.search(r"\b(\d+'\d+)\b", value)
    return (clean(length_match.group(1)) if length_match else None, None, None, volume)


def lost_geo_blocked(exc: Exception) -> SourceGeoBlockedError | None:
    message = str(exc)
    if "lostsurfboards.net" in message and "HTTP 403" in message:
        return SourceGeoBlockedError(LOST_US_REQUEST_FAILURE_REASON)
    return None


def lost_request_json(url: str, request_with_retry) -> object:
    try:
        return response_json(url, request_with_retry)
    except Exception as exc:
        geo_blocked = lost_geo_blocked(exc)
        if geo_blocked:
            raise geo_blocked from exc
        raise


def lost_resolve_category_id(request_with_retry) -> str | None:
    payload = lost_request_json(LOST_US_PRODUCT_CAT_API, request_with_retry)
    if not isinstance(payload, list):
        return None
    for category in payload:
        slug = clean(category.get("slug")).lower()
        if slug == "surfboards":
            category_id = category.get("id")
            return str(category_id) if category_id not in (None, "") else None
    return None


def fetch_lost_store_api_products(request_with_retry) -> list[dict]:
    category_id = lost_resolve_category_id(request_with_retry)
    products: list[dict] = []
    for endpoint in LOST_US_STORE_API_CANDIDATES:
        endpoint_products: list[dict] = []
        for page in range(1, 21):
            if category_id:
                url = f"{endpoint}?category={category_id}&page={page}&per_page=100"
            else:
                url = f"{endpoint}?search=surfboard&page={page}&per_page=100"
            payload = lost_request_json(url, request_with_retry)
            if not isinstance(payload, list):
                break
            if not payload:
                break
            endpoint_products.extend(item for item in payload if isinstance(item, dict))
            if len(payload) < 100:
                break
        if endpoint_products:
            products.extend(endpoint_products)
            break
    return products


def build_lost_rows(request_with_retry) -> list[dict]:
    products = fetch_lost_store_api_products(request_with_retry)
    checked_at = utc_now()
    rows: list[dict] = []
    seen = set()
    for product in products:
        if not looks_like_lost_surfboard(product):
            continue
        if not lost_is_available(product):
            continue
        raw_title = clean(product.get("name"))
        combined_text = " | ".join(
            item
            for item in (
                raw_title,
                clean(product.get("short_description")),
                clean(product.get("description")),
            )
            if item
        )
        length, width, thickness, volume = parse_lost_dimensions(combined_text)
        if not length or volume is None:
            continue
        product_url = clean(product.get("permalink")) or LOST_US_CATEGORY_URL
        row = {
            "brandName": "Lost",
            "modelName": normalise_lost_model_name(raw_title) or raw_title,
            "rawProductTitle": raw_title,
            "sourceUrl": product_url,
            "productUrl": product_url,
            "productImageUrl": lost_image_url(product),
            "priceAmount": lost_price_amount(product),
            "priceCurrency": lost_price_currency(product),
            "stockStatus": "available",
            "isAvailable": True,
            "availabilitySource": SOURCE,
            "regionCode": REGION_CODE,
            "lengthFeetInches": length,
            "width": width,
            "thickness": thickness,
            "volumeLitres": volume,
            "construction": normalise_construction(combined_text),
            "finSetup": normalise_fin_system(combined_text),
            "tailShape": parse_tail_shape(combined_text),
            "sourceProductId": str(product.get("id") or ""),
            "sourceVariantId": str(product.get("id") or ""),
            "sourceVariantTitle": clean(product.get("sku")) or raw_title,
            "lastCheckedUtc": checked_at,
        }
        dedupe_key = (
            row["modelName"],
            row["lengthFeetInches"],
            row["width"],
            row["thickness"],
            row["volumeLitres"],
            row["construction"],
            row["productUrl"],
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        rows.append(row)
    return dedupe_rows(rows)


def output_path_for_slug(slug: str) -> Path:
    return OUTPUT_ROOT / slug / "output" / f"{slug}_us_manufacturer_inventory.json"


def load_existing_output(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        row
        for row in rows
        if row.get("regionCode") == REGION_CODE
        and row.get("availabilitySource") == SOURCE
    ]


def response_json(url: str, request_with_retry) -> object:
    response = request_with_retry(url)
    return response.json()


def money(value: object) -> float | None:
    if value in (None, ""):
        return None
    text = clean(value).replace("$", "").replace(",", "")
    try:
        return round(float(text), 2)
    except (TypeError, ValueError):
        return None


def product_image(product: dict, variant: dict | None = None) -> str | None:
    featured = (variant or {}).get("featured_image") or {}
    if isinstance(featured, dict) and clean(featured.get("src")):
        return clean(featured.get("src"))
    images = product.get("images") or []
    for image in images:
        if isinstance(image, dict) and clean(image.get("src")):
            return clean(image.get("src"))
    image = product.get("image")
    if isinstance(image, dict):
        return clean(image.get("src")) or None
    return None


def shopify_product_url(base_url: str, handle: str, variant_id: object | None) -> str:
    suffix = f"?variant={variant_id}" if variant_id else ""
    return f"{base_url.rstrip('/')}/products/{handle}{suffix}"


def build_row(
    *,
    brand_name: str,
    model_name: str,
    raw_title: str,
    product_url: str,
    image_url: str | None,
    checked_at: str,
    price_amount: float | None,
    price_currency: str | None,
    length: str | None,
    width: str | None,
    thickness: str | None,
    volume: float | None,
    construction: str | None,
    fin_setup: str | None,
    tail_shape: str | None,
    source_product_id: object,
    source_variant_id: object,
    source_variant_title: object,
) -> dict:
    return {
        "brandName": brand_name,
        "modelName": clean(model_name),
        "rawProductTitle": clean(raw_title),
        "sourceUrl": product_url,
        "productUrl": product_url,
        "productImageUrl": image_url,
        "priceAmount": price_amount,
        "priceCurrency": clean(price_currency) or None,
        "stockStatus": "available",
        "isAvailable": True,
        "availabilitySource": SOURCE,
        "regionCode": REGION_CODE,
        "lengthFeetInches": length,
        "width": width,
        "thickness": thickness,
        "volumeLitres": volume,
        "construction": construction,
        "finSetup": fin_setup,
        "tailShape": tail_shape,
        "sourceProductId": str(source_product_id or ""),
        "sourceVariantId": str(source_variant_id or ""),
        "sourceVariantTitle": clean(source_variant_title),
        "lastCheckedUtc": checked_at,
    }


def dedupe_rows(rows: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        key = (
            row.get("brandName"),
            row.get("modelName"),
            row.get("lengthFeetInches"),
            row.get("width"),
            row.get("thickness"),
            row.get("volumeLitres"),
            row.get("construction"),
            row.get("productUrl"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def parse_variant_length(value: object) -> str | None:
    value = clean(value)
    match = re.search(r"\b([4-9]'\d{1,2})\b", value)
    return match.group(1) if match else None


def parse_tail_shape(value: object) -> str | None:
    lowered = clean(value).lower()
    if "swallow" in lowered:
        return "Swallow"
    if "round" in lowered:
        return "Round"
    if "squash" in lowered:
        return "Squash"
    if "pin" in lowered:
        return "Pin"
    return None


def parse_christenson_description(description: str) -> dict | None:
    base_match = CHRISTENSON_BASE_SPECS_RE.search(description)
    if not base_match:
        return None
    remainder = clean(description[base_match.end() :])
    fin_match = CHRISTENSON_FIN_RE.search(remainder)
    return {
        "length": normalise_length(base_match.group("length")),
        "width": normalise_dimension_text(base_match.group("width")),
        "thickness": normalise_dimension_text(base_match.group("thickness")),
        "volume": float(base_match.group("volume")),
        "fin_setup": normalise_fin_system(fin_match.group(0)) if fin_match else None,
    }


def load_misfit_catalogue() -> dict[tuple[str, str], list[dict]]:
    rows = json.loads(MISFIT_CATALOGUE_PATH.read_text(encoding="utf-8"))
    index: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        if not row.get("is_active", True):
            continue
        model = row.get("model")
        length = row.get("length")
        if not model or not length:
            continue
        key = (normalise_key(model), clean(length))
        index.setdefault(key, []).append(row)
    return index


def fetch_shopify_products(products_url: str, request_with_retry, page_limit: int = 50) -> list[dict]:
    products: list[dict] = []
    for page in range(1, 40):
        separator = "&" if "?" in products_url else "?"
        url = f"{products_url}{separator}limit={page_limit}&page={page}"
        response = request_with_retry(url)
        batch = response.json().get("products", [])
        if not batch:
            break
        products.extend(batch)
        if len(batch) < page_limit:
            break
    return products


def build_misfit_rows(request_with_retry) -> list[dict]:
    catalogue_index = load_misfit_catalogue()
    products = fetch_shopify_products(MISFIT_PRODUCTS_URL, request_with_retry)
    checked_at = utc_now()
    rows: list[dict] = []
    for product in products:
        if clean(product.get("product_type")).lower() != "surfboard":
            continue
        model_name = clean(product.get("title"))
        handle = clean(product.get("handle"))
        if not model_name or not handle:
            continue
        image_url = product_image(product)
        for variant in product.get("variants") or []:
            if not variant.get("available"):
                continue
            variant_title = clean(variant.get("title"))
            length = parse_variant_length(variant_title)
            if not length:
                continue
            canonical_rows = catalogue_index.get((normalise_key(model_name), length), [])
            if not canonical_rows:
                continue
            for canonical in canonical_rows:
                rows.append(
                    build_row(
                        brand_name="Misfit Shapes",
                        model_name=canonical.get("model") or model_name,
                        raw_title=model_name,
                        product_url=shopify_product_url(
                            MISFIT_SOURCE_STOREFRONT,
                            handle,
                            variant.get("id"),
                        ),
                        image_url=image_url or canonical.get("official_image_url"),
                        checked_at=checked_at,
                        price_amount=money(variant.get("price")),
                        price_currency=MISFIT_PRODUCT_CURRENCY,
                        length=clean(canonical.get("length")),
                        width=clean(canonical.get("width")),
                        thickness=clean(canonical.get("thickness")),
                        volume=float(canonical.get("volume_litres")),
                        construction=clean(canonical.get("construction")),
                        fin_setup=None,
                        tail_shape=parse_tail_shape(variant_title) or clean(canonical.get("tail_shape")),
                        source_product_id=product.get("id"),
                        source_variant_id=variant.get("id"),
                        source_variant_title=variant_title,
                    )
                )
    return dedupe_rows(rows)


def build_pukas_rows(request_with_retry) -> list[dict]:
    products = fetch_shopify_products(PUKAS_PRODUCTS_URL, request_with_retry)
    checked_at = utc_now()
    rows: list[dict] = []
    for product in products:
        if clean(product.get("product_type")).upper() != "SURFBOARDS":
            continue
        title = clean(product.get("title"))
        match = PUKAS_TITLE_RE.search(title)
        if not match:
            continue
        handle = clean(product.get("handle"))
        if not handle:
            continue
        variants = product.get("variants") or []
        for variant in variants:
            if not variant.get("available"):
                continue
            rows.append(
                build_row(
                    brand_name="Pukas",
                    model_name=match.group("model"),
                    raw_title=title,
                    product_url=shopify_product_url(
                        PUKAS_SOURCE_STOREFRONT,
                        handle,
                        variant.get("id"),
                    ),
                    image_url=product_image(product, variant),
                    checked_at=checked_at,
                    price_amount=money(variant.get("price")),
                    price_currency=PUKAS_PRODUCT_CURRENCY,
                    length=normalise_length(match.group("length")),
                    width=normalise_dimension_text(match.group("width")),
                    thickness=normalise_dimension_text(match.group("thickness")),
                    volume=float(match.group("volume")),
                    construction=None,
                    fin_setup=None,
                    tail_shape=None,
                    source_product_id=product.get("id"),
                    source_variant_id=variant.get("id"),
                    source_variant_title=match.group("source_code") or variant.get("title"),
                )
            )
    return dedupe_rows(rows)


def build_christenson_rows(request_with_retry) -> list[dict]:
    listing_html = request_with_retry(CHRISTENSON_STOCK_URL).text
    checked_at = utc_now()
    rows: list[dict] = []
    for block in CHRISTENSON_PRODUCT_BLOCK_RE.finditer(listing_html):
        image_match = CHRISTENSON_IMAGE_RE.search(block.group("body"))
        title_card_match = CHRISTENSON_PRODUCT_TITLE_RE.search(block.group("body"))
        price_card_match = CHRISTENSON_PRODUCT_PRICE_RE.search(block.group("body"))
        if not image_match or not title_card_match or not price_card_match:
            continue
        relative_href = block.group("href")
        product_url = f"https://christensonsurfboards.com{relative_href}"
        detail_html = request_with_retry(product_url).text
        description_match = CHRISTENSON_DETAIL_RE.search(detail_html)
        title_match = CHRISTENSON_TITLE_RE.search(detail_html)
        price_match = CHRISTENSON_PRICE_RE.search(detail_html)
        if not description_match or not title_match:
            continue
        description = clean(description_match.group("description"))
        parsed_specs = parse_christenson_description(description)
        if not parsed_specs:
            continue
        title = clean(title_match.group("title"))
        title = re.sub(r"\s*[—-]\s*Christenson surfboards$", "", title, flags=re.I)
        model_name = re.sub(r"^[4-9]'\d{1,2}\s*", "", title).strip()
        rows.append(
            build_row(
                brand_name="Christenson",
                model_name=model_name,
                raw_title=clean(title_card_match.group("title")),
                product_url=product_url,
                image_url=clean(image_match.group("image")),
                checked_at=checked_at,
                price_amount=money(price_match.group("price") if price_match else price_card_match.group("price")),
                price_currency="USD",
                length=parsed_specs["length"],
                width=parsed_specs["width"],
                thickness=parsed_specs["thickness"],
                volume=parsed_specs["volume"],
                construction=None,
                fin_setup=parsed_specs["fin_setup"],
                tail_shape=None,
                source_product_id=relative_href,
                source_variant_id=relative_href,
                source_variant_title=description,
            )
        )
    return dedupe_rows(rows)


def fetch_chilli_models(request_with_retry) -> list[dict]:
    response = request_with_retry(CHILLI_MODELS_URL)
    payload = response.json()
    return payload if isinstance(payload, list) else []


def fetch_chilli_detail(model_id: object, request_with_retry) -> dict:
    response = request_with_retry(CHILLI_DETAIL_URL.format(id=model_id))
    payload = response.json()
    if isinstance(payload, list):
        return payload[0] if payload else {}
    return payload if isinstance(payload, dict) else {}


def is_chilli_dimension_available(dimension: dict) -> bool:
    value = str(dimension.get("shopavailable")).lower()
    if value in {"1", "true", "yes", "available"}:
        return True
    current = dimension.get("currentavailability")
    try:
        return float(current) > 0
    except (TypeError, ValueError):
        return False


def first_chilli_image(item: dict) -> str | None:
    img_dynamic = item.get("img_dynamic") or {}
    if isinstance(img_dynamic, dict):
        dynamic_image = img_dynamic.get("deck") or img_dynamic.get("bottom")
        if dynamic_image:
            return dynamic_image
    img = item.get("img") or {}
    if isinstance(img, dict):
        for image_data in img.values():
            if isinstance(image_data, dict):
                image_url = image_data.get("img_dynamic") or image_data.get("url")
                if image_url:
                    return image_url
    return item.get("img_logo") or item.get("img_deck") or item.get("img_bottom") or None


def fetch_chilli_storefront_map(request_with_retry) -> dict[str, dict]:
    html_text = request_with_retry(CHILLI_STOREFRONT_URL).text
    mapping: dict[str, dict] = {}
    for match in CHILLI_STOREFRONT_MODEL_RE.finditer(html_text):
        model_name = clean(match.group("model"))
        mapping[model_name] = {
            "product_url": f"https://www.chillisurfboards.com{match.group('href')}",
            "product_image_url": clean(match.group("image")),
            "price_amount": money(match.group("price")),
            "price_currency": clean(match.group("currency")),
            "model_id": clean(match.group("model_id")),
        }
    return mapping


def build_chilli_rows(request_with_retry) -> list[dict]:
    storefront_map = fetch_chilli_storefront_map(request_with_retry)
    checked_at = utc_now()
    rows: list[dict] = []
    for model in fetch_chilli_models(request_with_retry):
        model_id = clean(model.get("id_surfboardmodel"))
        model_name = clean(model.get("surfboardmodel"))
        if not model_id or not model_name:
            continue
        detail = fetch_chilli_detail(model_id, request_with_retry)
        dimensions = detail.get("standard_dimensions") or []
        if not dimensions:
            continue
        storefront = storefront_map.get(model_name, {})
        for dimension in dimensions:
            if not is_chilli_dimension_available(dimension):
                continue
            length = clean(dimension.get("length_inches"))
            width = clean(dimension.get("width_inches"))
            thickness = clean(dimension.get("thickness_inches"))
            volume = money(dimension.get("volume"))
            if not length or not width or not thickness or volume is None:
                continue
            variant_title = f"{length} x {width} x {thickness} {volume:g}L"
            rows.append(
                build_row(
                    brand_name="Chilli",
                    model_name=model_name,
                    raw_title=f"{model_name} {variant_title}",
                    product_url=storefront.get("product_url")
                    or f"https://www.chillisurfboards.com/surfboards/detail.php?id={model_id}&direct=1&region=usa",
                    image_url=storefront.get("product_image_url") or first_chilli_image(detail),
                    checked_at=checked_at,
                    price_amount=storefront.get("price_amount"),
                    price_currency=storefront.get("price_currency"),
                    length=length,
                    width=width,
                    thickness=thickness,
                    volume=float(volume),
                    construction=normalise_construction(
                        dimension.get("surfboardconstructiontype")
                        or detail.get("surfboardconstructiontype")
                    ),
                    fin_setup=normalise_fin_system(
                        f"{clean(detail.get('finsystem'))} {clean(detail.get('fin_no'))}"
                    ),
                    tail_shape=clean(dimension.get("tail")) or clean(detail.get("tailname")),
                    source_product_id=model_id,
                    source_variant_id=dimension.get("id"),
                    source_variant_title=variant_title,
                )
            )
    return dedupe_rows(rows)


def build_fresh(slug: str, request_with_retry) -> dict:
    target = EXTRA_TARGETS[slug]
    if slug == "christenson":
        rows = build_christenson_rows(request_with_retry)
    elif slug == "misfit":
        rows = build_misfit_rows(request_with_retry)
    elif slug == "chilli":
        rows = build_chilli_rows(request_with_retry)
    elif slug == "pukas":
        rows = build_pukas_rows(request_with_retry)
    else:
        raise RuntimeError(f"Unsupported additional US MFA brand: {slug}")
    if not rows:
        raise RuntimeError(f"No valid US MFA rows were built for {target['brand_name']}")
    output_path = output_path_for_slug(slug)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "slug": slug,
        "brand": target["brand_name"],
        "source_url": target["source_url"],
        "source_status": "fresh",
        "fresh_build_success": True,
        "used_stale_fallback": False,
        "error_type": None,
        "error_message_summary": None,
        "discovered_products": len(rows),
        "normalised_rows": len(rows),
        "available_rows": sum(1 for row in rows if row.get("isAvailable")),
        "rows_with_dimensions": sum(1 for row in rows if row.get("lengthFeetInches")),
        "rows_emitted": len(rows),
        "output": str(output_path),
        "regionCode": REGION_CODE,
        "priceCurrency": None,
    }


def build(slug: str, request_with_retry) -> dict:
    output_path = output_path_for_slug(slug)
    try:
        return build_fresh(slug, request_with_retry)
    except Exception as exc:
        allow_stale_fallback = EXTRA_TARGETS[slug].get("allow_stale_fallback", True)
        stale_rows = load_existing_output(output_path)
        if stale_rows and allow_stale_fallback:
            return {
                "slug": slug,
                "brand": EXTRA_TARGETS[slug]["brand_name"],
                "source_url": EXTRA_TARGETS[slug]["source_url"],
                "source_status": "stale_fallback",
                "fresh_build_success": False,
                "used_stale_fallback": True,
                "error_type": type(exc).__name__,
                "error_message_summary": str(exc),
                "discovered_products": None,
                "normalised_rows": len(stale_rows),
                "available_rows": sum(1 for row in stale_rows if row.get("isAvailable")),
                "rows_with_dimensions": sum(1 for row in stale_rows if row.get("lengthFeetInches")),
                "rows_emitted": len(stale_rows),
                "output": str(output_path),
                "regionCode": REGION_CODE,
                "priceCurrency": None,
            }
        source_status = "failed"
        if isinstance(exc, SourceGeoBlockedError):
            source_status = LOST_US_REQUEST_FAILURE_REASON
        return {
            "slug": slug,
            "brand": EXTRA_TARGETS[slug]["brand_name"],
            "source_url": EXTRA_TARGETS[slug]["source_url"],
            "source_status": source_status,
            "fresh_build_success": False,
            "used_stale_fallback": False,
            "error_type": type(exc).__name__,
            "error_message_summary": str(exc),
            "discovered_products": None,
            "normalised_rows": 0,
            "available_rows": 0,
            "rows_with_dimensions": 0,
            "rows_emitted": 0,
            "output": str(output_path),
            "regionCode": REGION_CODE,
            "priceCurrency": None,
        }
