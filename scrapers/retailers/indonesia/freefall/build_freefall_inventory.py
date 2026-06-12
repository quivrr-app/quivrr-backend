import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URLS = [
    "https://freefallsurfindustries.com/wp-json/wc/store/products?per_page=100",
    "https://freefallsurfindustries.com/wp-json/wc/store/products?per_page=100&page=2",
]

OUT_DIR = Path("scrapers/retailers/indonesia/freefall/output")
RAW_PATH = OUT_DIR / "freefall_raw_products.json"
SURFBOARDS_PATH = OUT_DIR / "freefall_surfboards.json"

SIZE_RE = re.compile(r"\b([4-9])['’](\d{1,2})")
VOLUME_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*L\b", re.I)

def fetch_json(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def clean_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip().replace("’", "'")

def money(product):
    try:
        return float((product.get("prices") or {}).get("price"))
    except (TypeError, ValueError):
        return None

def currency(product):
    return (product.get("prices") or {}).get("currency_code") or "AUD"

def image_url(product):
    images = product.get("images") or []
    return images[0].get("src") if images else None

def extract_size(text):
    m = SIZE_RE.search(text)
    return f"{m.group(1)}'{m.group(2)}" if m else None

def extract_volume(text):
    m = VOLUME_RE.search(text)
    return float(m.group(1)) if m else None

def extract_fin_setup(text):
    value = text.upper()
    if "FCS II" in value or "FCSII" in value:
        return "FCS II"
    if "FUTURES" in value:
        return "Futures"
    return None

def build_rows(products):
    rows = []
    checked_at = datetime.now(timezone.utc).isoformat()

    for product in products:
        permalink = product.get("permalink") or ""
        if "/surfboards/" not in permalink:
            continue

        name = clean_text(product.get("name"))
        desc = clean_text(product.get("short_description"))
        combined = f"{name} {desc}"

        rows.append({
            "retailerName": "Freefall Surf Industries",
            "regionCode": "ID",
            "countryCode": "ID",
            "currencyCode": currency(product),
            "brandName": None,
            "rawProductTitle": name,
            "variantTitle": None,
            "productUrl": permalink,
            "productImageUrl": image_url(product),
            "priceAmount": money(product),
            "stockStatus": "in stock" if product.get("is_in_stock") else "out of stock",
            "isAvailable": bool(product.get("is_in_stock")),
            "lengthFeetInches": extract_size(combined),
            "width": None,
            "thickness": None,
            "volumeLitres": extract_volume(combined),
            "finSetup": extract_fin_setup(combined),
            "construction": None,
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

    print(f"Freefall products: {len(products)}")
    print(f"Freefall surfboard rows: {len(rows)}")
    print(f"In stock: {sum(1 for r in rows if r.get('isAvailable'))}")
    print(f"With length: {sum(1 for r in rows if r.get('lengthFeetInches'))}")
    print(f"With volume: {sum(1 for r in rows if r.get('volumeLitres'))}")
    print(f"Output: {SURFBOARDS_PATH}")

    for row in rows[:20]:
        print(f"{row['stockStatus']} | {row['rawProductTitle']} | {row.get('lengthFeetInches')} | {row.get('volumeLitres')}L | {row['priceAmount']} {row['currencyCode']}")

if __name__ == "__main__":
    main()
