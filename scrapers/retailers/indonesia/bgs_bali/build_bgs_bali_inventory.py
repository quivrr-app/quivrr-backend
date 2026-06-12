import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE_URL = "https://store.bgsbali.com"
SOURCE_URL = f"{BASE_URL}/collections/surfboards/products.json?limit=250"

OUT_DIR = Path("scrapers/retailers/indonesia/bgs_bali/output")
RAW_PATH = OUT_DIR / "bgs_bali_raw_products.json"
SURFBOARDS_PATH = OUT_DIR / "bgs_bali_surfboards.json"

SIZE_RE = re.compile(r"\b([4-9])['’](\d{1,2})\b")
VOLUME_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*L\b", re.I)

SURFBOARD_TERMS = [
    "surfboard",
    "pyzel",
    "lost",
    "dhd",
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


def money_from_string(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_surfboard(product):
    haystack = " ".join([
        str(product.get("title") or ""),
        str(product.get("handle") or ""),
        str(product.get("body_html") or ""),
        " ".join(str(tag) for tag in product.get("tags") or []),
        str(product.get("product_type") or ""),
        str(product.get("vendor") or ""),
    ]).lower()

    return any(term in haystack for term in SURFBOARD_TERMS)


def extract_size(text):
    if not text:
        return None
    match = SIZE_RE.search(text.replace("’", "'"))
    if not match:
        return None
    return f"{match.group(1)}'{match.group(2)}"


def extract_volume_litres(text):
    if not text:
        return None
    match = VOLUME_RE.search(text)
    if not match:
        return None
    return float(match.group(1))


def extract_fin_setup(text):
    value = (text or "").upper().replace(".", "").replace(" ", "")
    if "FCSII" in value:
        return "FCS II"
    if "FUTURES" in value or "FUT" in value:
        return "Futures"
    return None


def extract_construction(text):
    value = f" {(text or '').upper()} "
    if " X RT X " in value or " RT " in value:
        return "RT"
    if " PU " in value:
        return "PU"
    if " EPS " in value:
        return "EPS"
    return None


def build_rows(products):
    rows = []
    checked_at = datetime.now(timezone.utc).isoformat()

    for product in products:
        if not is_surfboard(product):
            continue

        title = product.get("title") or ""
        handle = product.get("handle") or ""
        product_url = f"{BASE_URL}/products/{handle}" if handle else None

        images = product.get("images") or []
        image_url = images[0].get("src") if images else None

        for variant in product.get("variants") or []:
            variant_title = variant.get("title") or ""
            combined_text = " ".join([title, variant_title])
            available = bool(variant.get("available"))

            rows.append({
                "retailerName": "BGS Bali",
                "regionCode": "ID",
                "countryCode": "ID",
                "currencyCode": "IDR",
                "brandName": product.get("vendor"),
                "rawProductTitle": title,
                "variantTitle": variant_title,
                "productUrl": product_url,
                "productImageUrl": image_url,
                "priceAmount": money_from_string(variant.get("price")),
                "stockStatus": "in stock" if available else "out of stock",
                "isAvailable": available,
                "lengthFeetInches": extract_size(combined_text),
                "volumeLitres": extract_volume_litres(combined_text),
                "finSetup": extract_fin_setup(combined_text),
                "construction": extract_construction(combined_text),
                "sourcePlatform": "shopify",
                "sourceProductId": product.get("id"),
                "sourceVariantId": variant.get("id"),
                "lastCheckedUtc": checked_at,
            })

    return rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = fetch_json(SOURCE_URL)
    products = payload.get("products") or []
    rows = build_rows(products)

    RAW_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    SURFBOARDS_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"BGS products: {len(products)}")
    print(f"BGS surfboard rows: {len(rows)}")
    print(f"In stock: {sum(1 for row in rows if row.get('isAvailable'))}")
    print(f"With length: {sum(1 for row in rows if row.get('lengthFeetInches'))}")
    print(f"With volume: {sum(1 for row in rows if row.get('volumeLitres'))}")
    print(f"With fins: {sum(1 for row in rows if row.get('finSetup'))}")
    print(f"With construction: {sum(1 for row in rows if row.get('construction'))}")
    print(f"Output: {SURFBOARDS_PATH}")

    for row in rows[:20]:
        print(
            f"{row['stockStatus']} | {row['brandName']} | {row['rawProductTitle']} | "
            f"{row['variantTitle']} | {row.get('lengthFeetInches')} | "
            f"{row.get('volumeLitres')}L | {row.get('finSetup')} | "
            f"{row.get('construction')} | {row['priceAmount']} {row['currencyCode']}"
        )


if __name__ == "__main__":
    main()
