import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

SOURCE_URL = "https://driftersurf.com/collections/surfboards/products.json?limit=250"
BASE_URL = "https://driftersurf.com"

OUT_DIR = Path("scrapers/retailers/indonesia/drifter/output")
RAW_PATH = OUT_DIR / "drifter_raw_products.json"
SURFBOARDS_PATH = OUT_DIR / "drifter_surfboards.json"

SIZE_RE = re.compile(r"\b([4-9])['’](\d{1,2})\b")
VOL_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*L\b", re.I)

def clean_text(value):
    value = html.unescape(str(value or ""))
    value = value.replace("’", "'")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def get_price(product):
    variant = (product.get("variants") or [{}])[0]
    try:
        return float(variant.get("price"))
    except (TypeError, ValueError):
        return None

def get_available(product):
    variant = (product.get("variants") or [{}])[0]
    return bool(variant.get("available"))

def parse_brand(title):
    if title.startswith("Lost x Drifter"):
        return "Lost"
    if title.startswith("Pyzel x Drifter"):
        return "Pyzel"
    return "Drifter Surf"

def parse_model(title):
    return title.replace("Lost x Drifter -", "").replace("Pyzel x Drifter -", "").strip()

def extract_size(text):
    m = SIZE_RE.search(text)
    return f"{m.group(1)}'{m.group(2)}" if m else None

def extract_volume(text):
    m = VOL_RE.search(text)
    return float(m.group(1)) if m else None

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    products = requests.get(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    ).json()["products"]

    RAW_PATH.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")

    checked_at = datetime.now(timezone.utc).isoformat()
    rows = []

    for product in products:
        title = clean_text(product.get("title"))
        body = clean_text(product.get("body_html"))
        combined = f"{title} {body}"

        rows.append({
            "retailerName": "Drifter Surf",
            "regionCode": "ID",
            "countryCode": "ID",
            "currencyCode": "USD",
            "brandName": parse_brand(title),
            "modelName": parse_model(title),
            "rawProductTitle": title,
            "variantTitle": None,
            "productUrl": f"{BASE_URL}/products/{product.get('handle')}",
            "productImageUrl": (product.get("images") or [{}])[0].get("src"),
            "priceAmount": get_price(product),
            "stockStatus": "in stock" if get_available(product) else "out of stock",
            "isAvailable": get_available(product),
            "lengthFeetInches": extract_size(combined),
            "width": None,
            "thickness": None,
            "volumeLitres": extract_volume(combined),
            "finSetup": None,
            "construction": None,
            "sourcePlatform": "shopify",
            "sourceProductId": product.get("id"),
            "sourceVariantId": (product.get("variants") or [{}])[0].get("id"),
            "lastCheckedUtc": checked_at,
        })

    SURFBOARDS_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Rows:", len(rows))
    for row in rows:
        print(row["brandName"], "|", row["modelName"], "|", row["priceAmount"], row["currencyCode"])

if __name__ == "__main__":
    main()
