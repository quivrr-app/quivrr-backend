import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://id.jsindustries.com"
PRODUCTS_URL = f"{BASE_URL}/products.json"
OUT_DIR = Path("scrapers/manufacturers/availability/output/js_industries")
RAW_PATH = OUT_DIR / "js_id_raw_products.json"
OUT_PATH = OUT_DIR / "js_id_manufacturer_inventory.json"

TITLE_RE = re.compile(
    r"^(?P<model>.*?)\s+"
    r"(?P<length>[4-9]'\d{1,2})\"?\s*x\s*"
    r"(?P<width>.*?)\s+X\s+"
    r"(?P<thickness>.*?)\s*-\s*"
    r"(?P<volume>\d+(?:\.\d+)?)L,\s*"
    r"(?P<tail>.*?),\s*"
    r"(?P<fin_no>\d+)x\s*(?P<fin_system>.*?)\s*Fin Boxes.*?,\s*"
    r"(?P<construction>[A-Za-z0-9.\- ]+)\s*-\s*ID:(?P<source_id>\d+)",
    re.I,
)

def clean(value):
    value = html.unescape(str(value or ""))
    value = value.replace("?", "'").replace("?", '"').replace("?", '"')
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def norm_fin(value):
    low = clean(value).lower()
    if "fcs" in low:
        return "FCS II"
    if "future" in low:
        return "Futures"
    return clean(value) or None

def norm_construction(value):
    value = clean(value).upper()
    if value in {"PE", "PU"}:
        return "PU"
    if "HYFI" in value:
        return "HYFI"
    return clean(value) or None

def fetch_products():
    products = []
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

    for page in range(1, 20):
        response = session.get(PRODUCTS_URL, params={"limit": 250, "page": page}, timeout=45)
        response.raise_for_status()
        batch = response.json().get("products") or []
        if not batch:
            break
        print(f"JS ID page {page}: {len(batch)}")
        products.extend(batch)

    return products

def parse_product(product, checked_at):
    title = clean(product.get("title"))
    match = TITLE_RE.search(title)

    if not match:
        return None

    variant = (product.get("variants") or [{}])[0]
    price = None

    try:
        price = float(variant.get("price"))
    except (TypeError, ValueError):
        pass

    available = bool(variant.get("available"))

    return {
        "brandName": "JS Industries",
        "regionCode": "ID",
        "countryCode": "ID",
        "currencyCode": "IDR",
        "availabilitySource": "manufacturer_direct",
        "modelName": clean(match.group("model")),
        "rawProductTitle": title,
        "productUrl": f"{BASE_URL}/products/{product.get('handle')}",
        "productImageUrl": (product.get("images") or [{}])[0].get("src"),
        "priceAmount": price,
        "priceCurrency": "IDR",
        "stockStatus": "in stock" if available else "out of stock",
        "isAvailable": available,
        "construction": norm_construction(match.group("construction")),
        "lengthFeetInches": clean(match.group("length")),
        "width": clean(match.group("width")),
        "thickness": clean(match.group("thickness")),
        "volumeLitres": float(match.group("volume")),
        "finSetup": norm_fin(match.group("fin_system")),
        "tailShape": clean(match.group("tail")),
        "sourceProductId": str(product.get("id")),
        "sourceVariantId": str(variant.get("id")),
        "sourceVariantTitle": clean(variant.get("title")),
        "manufacturerSourceId": clean(match.group("source_id")),
        "lastCheckedUtc": checked_at,
    }

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    products = fetch_products()
    RAW_PATH.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")

    checked_at = datetime.now(timezone.utc).isoformat()
    rows = [parse_product(p, checked_at) for p in products]
    rows = [r for r in rows if r]

    if not rows:
        raise RuntimeError("No JS Indonesia MFA rows parsed")

    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print("JS ID products:", len(products))
    print("JS ID MFA rows:", len(rows))
    print("Available:", sum(1 for r in rows if r["isAvailable"]))
    print("With board size fields:", sum(1 for r in rows if r.get("lengthFeetInches") and r.get("volumeLitres")))
    print("Output:", OUT_PATH)

if __name__ == "__main__":
    main()
