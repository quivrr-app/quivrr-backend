import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.onboardstore.id/shop?shop=surfboards&id_usedstate=0%2C1%2C4"
BASE_URL = "https://www.onboardstore.id"

OUT_DIR = Path("scrapers/retailers/indonesia/onboard_store/output")
RAW_PATH = OUT_DIR / "onboard_store_raw.html"
SURFBOARDS_PATH = OUT_DIR / "onboard_store_surfboards.json"

PRICE_RE = re.compile(r"\b(\d{1,2}(?:\s\d{3}){2})\b")
SIZE_RE = re.compile(
    r"(?P<length>[4-9]'\d{1,2})\"?\s*x\s*"
    r"(?P<width>[^x]+?)\"\s*x\s*"
    r"(?P<thickness>[^-]+?)\"\s*-\s*"
    r"(?P<volume>\d+(?:\.\d+)?)\s*L",
    re.I,
)

FIN_RE = re.compile(r"(FCS|Futures)\s+Fin System", re.I)

KNOWN_BRANDS = [
    "Channel Islands",
    "Crowe Surfboards",
    "Christenson",
    "Pyzel",
    "Lost",
    "DHD",
    "JS Industries",
    "Album",
    "Firewire",
    "Sharp Eye",
    "Sharpeye",
    "Chilli",
]


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = value.replace("’", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value).strip()
    return value


def absolute_url(href):
    if href.startswith("http"):
        return href
    return BASE_URL + href


def parse_brand(text):
    for brand in KNOWN_BRANDS:
        if text.lower().startswith(brand.lower()):
            return brand
    return text.split(" ", 1)[0] if text else None


def parse_model(text, brand):
    if not brand:
        return text

    model = text[len(brand):].strip()

    size_match = re.search(r"\b[4-9]'\d{1,2}", model)
    if size_match:
        model = model[:size_match.start()].strip()

    return model.strip(" -")


def parse_price(text):
    matches = PRICE_RE.findall(text)
    if not matches:
        return None
    raw = matches[-1].replace(" ", "")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_row(href, text):
    text = clean_text(text)

    size_match = SIZE_RE.search(text)
    if not size_match:
        return None

    brand = parse_brand(text)
    model = parse_model(text, brand)
    price = parse_price(text)
    fin_match = FIN_RE.search(text)

    stock_status = "in stock"
    if re.search(r"\bout of stock\b|\bsold\b", text, re.I):
        stock_status = "out of stock"

    return {
        "retailerName": "Onboard Store Indonesia",
        "regionCode": "ID",
        "countryCode": "ID",
        "currencyCode": "IDR",
        "brandName": brand,
        "modelName": model,
        "rawProductTitle": text,
        "variantTitle": None,
        "productUrl": absolute_url(href),
        "productImageUrl": None,
        "priceAmount": price,
        "stockStatus": stock_status,
        "isAvailable": stock_status == "in stock",
        "lengthFeetInches": size_match.group("length"),
        "width": clean_text(size_match.group("width")),
        "thickness": clean_text(size_match.group("thickness")),
        "volumeLitres": float(size_match.group("volume")),
        "finSetup": fin_match.group(1).title() if fin_match else None,
        "construction": None,
        "sourcePlatform": "custom_html",
        "sourceProductId": re.search(r"id=(\d+)", href).group(1) if re.search(r"id=(\d+)", href) else None,
        "sourceVariantId": None,
        "lastCheckedUtc": datetime.now(timezone.utc).isoformat(),
    }


def fetch_html():
    response = requests.get(
        SOURCE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    page = fetch_html()
    RAW_PATH.write_text(page, encoding="utf-8")

    soup = BeautifulSoup(page, "html.parser")
    rows = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/shop/details/" not in href:
            continue

        row = parse_row(href, a.get_text(" ", strip=True))

        if not row:
            continue

        key = (row["sourceProductId"], row["rawProductTitle"])
        if key in seen:
            continue

        seen.add(key)
        rows.append(row)

    SURFBOARDS_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Onboard rows: {len(rows)}")
    print(f"In stock: {sum(1 for row in rows if row.get('isAvailable'))}")
    print(f"With price: {sum(1 for row in rows if row.get('priceAmount'))}")
    print(f"With length: {sum(1 for row in rows if row.get('lengthFeetInches'))}")
    print(f"With volume: {sum(1 for row in rows if row.get('volumeLitres'))}")

    for row in rows[:20]:
        print(
            f"{row['stockStatus']} | {row['brandName']} | {row['modelName']} | "
            f"{row['lengthFeetInches']} | {row['volumeLitres']}L | "
            f"{row['finSetup']} | {row['priceAmount']} {row['currencyCode']}"
        )


if __name__ == "__main__":
    main()
