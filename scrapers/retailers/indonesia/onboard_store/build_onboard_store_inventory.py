import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://www.onboardstore.id"
API_URL = "https://onboardbali.shaperbuddy.com/api/v1/shop/surfboards"

OUT_DIR = Path("scrapers/retailers/indonesia/onboard_store/output")
RAW_PATH = OUT_DIR / "onboard_store_raw_api.json"
SURFBOARDS_PATH = OUT_DIR / "onboard_store_surfboards.json"

DIM_RE = re.compile(
    r"(?P<length>[4-9]'\d{1,2})\"?\s*x\s*"
    r"(?P<width>[^x]+?)\"?\s*x\s*"
    r"(?P<thickness>[^-]+?)\"?\s*-\s*"
    r"(?P<volume>\d+(?:\.\d+)?)?\s*L",
    re.I,
)

KNOWN_BRANDS = [
    "Channel Islands",
    "Surf A Billy by Jared Mel",
    "Chris Christenson",
    "Crowe Surfboards",
    "Sharp Eye",
    "Sharpeye",
    "Lost",
    "Pyzel",
    "JS Industries",
    "DHD",
]


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = value.replace("?", "'").replace("?", '"').replace("?", '"')
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_price(value):
    value = clean_text(value)
    value = re.sub(r"[^\d]", "", value)
    return float(value) if value else None


def parse_brand(row):
    value = clean_text(
        row.get("brand")
        or row.get("brandname")
        or row.get("surfboardbrand")
        or row.get("label_brand")
    )

    if value:
        return value

    title = clean_text(row.get("name") or row.get("model") or row.get("title"))

    for brand in KNOWN_BRANDS:
        if title.lower().startswith(brand.lower()):
            return brand

    return None


def parse_model(row, brand):
    value = clean_text(
        row.get("model")
        or row.get("modelname")
        or row.get("surfboardmodel")
        or row.get("label_model")
        or row.get("name")
        or row.get("title")
    )

    if brand and value.lower().startswith(brand.lower()):
        value = value[len(brand):].strip()

    return value or None


def parse_fin(row, text):
    value = clean_text(
        row.get("finsystem")
        or row.get("fin_system")
        or row.get("fin")
        or row.get("label_finsystem")
    )

    if value:
        return value.replace("FCS", "FCS").replace("Futures", "Futures")

    if "Futures Fin System" in text:
        return "Futures"
    if "FCS" in text:
        return "FCS"

    return None


def parse_dimensions(text):
    match = DIM_RE.search(text)
    if not match:
        return None

    volume = match.group("volume")

    return {
        "lengthFeetInches": match.group("length"),
        "width": clean_text(match.group("width")),
        "thickness": clean_text(match.group("thickness")),
        "volumeLitres": float(volume) if volume else None,
    }


def fetch_all():
    rows = []

    for page in range(1, 50):
        response = requests.get(
            API_URL,
            params={
                "page": page,
                "per_page": 100,
                "id_usedstate": "0,1,4",
            },
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.onboardstore.id/shop?shop=surfboards&id_usedstate=0%2C1%2C4",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            break

        print(f"Onboard API page {page}: {len(data)}")
        rows.extend(data)

    return rows


def row_text(row):
    parts = []

    for key, value in row.items():
        if isinstance(value, (str, int, float)):
            parts.append(str(value))

    return clean_text(" ".join(parts))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    api_rows = fetch_all()

    RAW_PATH.write_text(
        json.dumps(api_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    checked_at = datetime.now(timezone.utc).isoformat()
    rows = []

    for item in api_rows:
        text = row_text(item)

        brand = clean_text(item.get("brand"))
        model = clean_text(item.get("surfboardmodel"))

        product_id = item.get("id_surfboard") or item.get("id")
        product_url = f"{BASE_URL}/shop/details/?shop=surfboards&id={product_id}" if product_id else BASE_URL

        img = item.get("img") or {}
        image_url = img.get("deck") or img.get("bottom") or img.get("default") if isinstance(img, dict) else None

        price = item.get("price") or item.get("webprice")

        dims = {
            "lengthFeetInches": clean_text(item.get("length_inches")).replace('"', ""),
            "width": clean_text(item.get("width_display")).replace('"', ""),
            "thickness": clean_text(item.get("thickness_display")).replace('"', ""),
            "volumeLitres": float(item.get("volume")) if clean_text(item.get("volume")) else None,
        }

        if not dims["lengthFeetInches"]:
            continue

        rows.append({
            "retailerName": "Onboard Store Indonesia",
            "regionCode": "ID",
            "countryCode": "ID",
            "currencyCode": "IDR",
            "brandName": brand,
            "modelName": model,
            "rawProductTitle": f"{brand} {model} {dims['lengthFeetInches']}",
            "variantTitle": None,
            "productUrl": product_url,
            "productImageUrl": image_url,
            "priceAmount": parse_price(price),
            "stockStatus": "in stock",
            "isAvailable": True,
            "lengthFeetInches": dims["lengthFeetInches"],
            "width": dims["width"],
            "thickness": dims["thickness"],
            "volumeLitres": dims["volumeLitres"],
            "finSetup": clean_text(item.get("finsystem")),
            "construction": clean_text(item.get("surfboardconstructiontype")),
            "sourcePlatform": "shaperbuddy_api",
            "sourceProductId": product_id,
            "sourceVariantId": None,
            "lastCheckedUtc": checked_at,
        })

    SURFBOARDS_PATH.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Onboard API rows: {len(api_rows)}")
    print(f"Onboard parsed rows: {len(rows)}")
    print(f"With price: {sum(1 for r in rows if r.get('priceAmount'))}")
    print(f"With volume: {sum(1 for r in rows if r.get('volumeLitres') is not None)}")

    for row in rows[:20]:
        print(
            f"{row['brandName']} | {row['modelName']} | "
            f"{row['lengthFeetInches']} | {row['volumeLitres']}L | "
            f"{row['priceAmount']} IDR"
        )


if __name__ == "__main__":
    main()
