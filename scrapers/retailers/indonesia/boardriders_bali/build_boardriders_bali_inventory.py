import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

SOURCE_URL = "https://boardridersbali.com/products.json?limit=250"

OUT_DIR = Path("scrapers/retailers/indonesia/boardriders_bali/output")
RAW_PATH = OUT_DIR / "boardriders_bali_raw_products.json"
SURFBOARDS_PATH = OUT_DIR / "boardriders_bali_surfboards.json"

DIM_RE = re.compile(
    r"([4-9]'\d{1,2})\s*x\s*"
    r"([0-9\s/]+)\s*x\s*"
    r"([0-9\s/]+)\s*[-=]\s*"
    r"([0-9]+(?:\.[0-9]+)?)L",
    re.I
)

def clean_text(value):
    value = html.unescape(str(value or ""))
    value = value.replace("’", "'")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def fetch_products():
    return requests.get(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    ).json()["products"]

def is_surfboard(product):
    title = product.get("title", "")

    if (
        title.startswith("DHD")
        or title.startswith("JS INDUSTRIES")
        or title.startswith("HaydenShapes")
        or title.startswith("NATIVE")
        or title in ["Twin Loves", "Moonzoomer"]
    ):
        return True

    return False

def parse_brand(title):
    if title.startswith("DHD"):
        return "DHD"

    if title.startswith("JS INDUSTRIES"):
        return "JS Industries"

    if title.startswith("HaydenShapes"):
        return "Hayden Shapes"

    if title.startswith("NATIVE"):
        return "Native"

    return "Other"

def parse_model(title, brand):
    if brand == "JS Industries":
        return title.replace("JS INDUSTRIES -", "").strip()

    if brand == "Hayden Shapes":
        return title.replace("HaydenShapes -", "").strip()

    if brand in ["DHD", "Native"]:
        return title.replace(brand, "").strip()

    return title

def extract_dimensions(body):

    rows = []

    for match in DIM_RE.finditer(body):
        rows.append({
            "lengthFeetInches": match.group(1),
            "width": match.group(2).strip(),
            "thickness": match.group(3).strip(),
            "volumeLitres": float(match.group(4)),
        })

    for match in re.finditer(
        r"([4-9]'\d{1,2})\s+"
        r"([0-9\s/]+)\s+"
        r"([0-9\s/]+)\s+"
        r"([0-9]+(?:\.[0-9]+)?)L",
        body,
        flags=re.I
    ):
        rows.append({
            "lengthFeetInches": match.group(1),
            "width": match.group(2).strip(),
            "thickness": match.group(3).strip(),
            "volumeLitres": float(match.group(4)),
        })

    seen = set()
    output = []

    for row in rows:
        key = (
            row["lengthFeetInches"],
            row["width"],
            row["thickness"],
            row["volumeLitres"],
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(row)

    return output

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    products = fetch_products()

    RAW_PATH.write_text(
        json.dumps(products, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    inventory_rows = []

    checked_at = datetime.now(timezone.utc).isoformat()

    for product in products:

        if not is_surfboard(product):
            continue

        title = clean_text(product.get("title"))
        brand = parse_brand(title)
        model = parse_model(title, brand)

        body = product.get("body_html", "")

        dimensions = extract_dimensions(body)

        if not dimensions:
            continue

        variant = (product.get("variants") or [{}])[0]

        for dim in dimensions:

            inventory_rows.append({
                "retailerName": "Boardriders Bali",
                "regionCode": "ID",
                "countryCode": "ID",
                "currencyCode": "IDR",
                "brandName": brand,
                "modelName": model,
                "rawProductTitle": title,
                "productUrl": f"https://boardridersbali.com/products/{product['handle']}",
                "priceAmount": float(variant.get("price") or 0),
                "stockStatus": "in stock" if variant.get("available") else "out of stock",
                "isAvailable": bool(variant.get("available")),
                "construction": None,
                "lengthFeetInches": dim["lengthFeetInches"],
                "width": dim["width"],
                "thickness": dim["thickness"],
                "volumeLitres": dim["volumeLitres"],
                "lastCheckedUtc": checked_at,
            })

    SURFBOARDS_PATH.write_text(
        json.dumps(inventory_rows, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("Rows:", len(inventory_rows))

if __name__ == "__main__":
    main()
