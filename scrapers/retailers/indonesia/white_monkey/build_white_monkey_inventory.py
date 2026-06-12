import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URLS = [
    "https://whitemonkeysurf.com/wp-json/wc/store/products?per_page=100&page=2",
]

OUT_DIR = Path("scrapers/retailers/indonesia/white_monkey/output")
RAW_PATH = OUT_DIR / "white_monkey_raw_products.json"
SURFBOARDS_PATH = OUT_DIR / "white_monkey_surfboards.json"

SIZE_RE = re.compile(r"\b([4-9])[’'](\d{1,2})\b")
DIMENSION_RE = re.compile(
    r"\b([4-9])[’'](\d{1,2})\s+"
    r"(\d+(?:\.\d+)?)\s+"
    r"(\d+(?:\.\d+)?)\s+"
    r"(\d+(?:\.\d+)?)\s*"
    r"([A-Z0-9 .-]+)?\b"
)

SURFBOARD_TERMS = [
    "surfboard",
    "lost",
    "dhd",
    "pyzel",
    "channel islands",
    "js industries",
    "album",
    "firewire",
    "chilli",
    "sharpeye",
    "sharp eye",
    "misfit",
    "chemistry",
    "haydenshapes",
]


def fetch_json(url):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_text(value):
    if value is None:
        return ""
    value = html.unescape(str(value))
    value = value.replace("\u2019", "'").replace("\u2018", "'")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def money_from_prices(product):
    prices = product.get("prices") or {}
    value = prices.get("price")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def currency_from_prices(product):
    prices = product.get("prices") or {}
    return prices.get("currency_code") or "IDR"


def is_surfboard(product):
    haystack = " ".join([
        clean_text(product.get("name")),
        clean_text(product.get("short_description")),
        clean_text(product.get("description")),
        clean_text(product.get("permalink")),
    ]).lower()

    return any(term in haystack for term in SURFBOARD_TERMS)


def image_url(product):
    images = product.get("images") or []
    return images[0].get("src") if images else None


def size_terms(product):
    terms = []
    for attr in product.get("attributes") or []:
        if str(attr.get("name") or "").lower() == "size":
            for term in attr.get("terms") or []:
                name = clean_text(term.get("name"))
                if name:
                    terms.append(name)
    return terms


def parse_dimension_term(term):
    text = clean_text(term).replace("’", "'")

    match = DIMENSION_RE.search(text)
    if not match:
        size_match = SIZE_RE.search(text)
        return {
            "lengthFeetInches": f"{size_match.group(1)}'{size_match.group(2)}" if size_match else None,
            "width": None,
            "thickness": None,
            "volumeLitres": None,
            "construction": None,
        }

    construction = (match.group(6) or "").strip(" .,-") or None

    return {
        "lengthFeetInches": f"{match.group(1)}'{match.group(2)}",
        "width": match.group(3),
        "thickness": match.group(4),
        "volumeLitres": float(match.group(5)),
        "construction": construction,
    }


def build_rows(products):
    rows = []
    checked_at = datetime.now(timezone.utc).isoformat()

    for product in products:
        if not is_surfboard(product):
            continue

        name = clean_text(product.get("name")).lstrip(".…").strip()
        terms = size_terms(product)

        if not terms:
            terms = [name]

        for term in terms:
            parsed = parse_dimension_term(term)

            rows.append({
                "retailerName": "White Monkey",
                "regionCode": "ID",
                "countryCode": "ID",
                "currencyCode": currency_from_prices(product),
                "brandName": name.split(" ", 1)[0] if name else None,
                "rawProductTitle": name,
                "variantTitle": term,
                "productUrl": product.get("permalink"),
                "productImageUrl": image_url(product),
                "priceAmount": money_from_prices(product),
                "stockStatus": "in stock" if product.get("is_in_stock") else "out of stock",
                "isAvailable": bool(product.get("is_in_stock")),
                "lengthFeetInches": parsed.get("lengthFeetInches"),
                "width": parsed.get("width"),
                "thickness": parsed.get("thickness"),
                "volumeLitres": parsed.get("volumeLitres"),
                "finSetup": None,
                "construction": parsed.get("construction"),
                "sourcePlatform": "woocommerce_store_api",
                "sourceProductId": product.get("id"),
                "sourceVariantId": None,
                "lastCheckedUtc": checked_at,
            })

    return rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    products = []
    for url in SOURCE_URLS:
        products.extend(fetch_json(url))

    rows = build_rows(products)

    RAW_PATH.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    SURFBOARDS_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"White Monkey products: {len(products)}")
    print(f"White Monkey surfboard rows: {len(rows)}")
    print(f"In stock: {sum(1 for row in rows if row.get('isAvailable'))}")
    print(f"With length: {sum(1 for row in rows if row.get('lengthFeetInches'))}")
    print(f"With volume: {sum(1 for row in rows if row.get('volumeLitres'))}")
    print(f"With construction: {sum(1 for row in rows if row.get('construction'))}")
    print(f"Output: {SURFBOARDS_PATH}")

    for row in rows[:20]:
        print(
            f"{row['stockStatus']} | {row['rawProductTitle']} | {row['variantTitle']} | "
            f"{row.get('lengthFeetInches')} | {row.get('volumeLitres')}L | "
            f"{row.get('construction')} | {row['priceAmount']} {row['currencyCode']}"
        )


if __name__ == "__main__":
    main()
