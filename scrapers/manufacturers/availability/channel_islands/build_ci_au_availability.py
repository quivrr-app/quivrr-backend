import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BRAND_NAME = "Channel Islands"
REGION_CODE = "AU"
BASE_URL = "https://shop-au.cisurfboards.com"
SOURCE_URL = "https://shop-au.cisurfboards.com/products.json?limit=250"

OUTPUT_FILE = Path(
    "scrapers/manufacturers/availability/output/channel_islands/ci_au_manufacturer_inventory.json"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://shop-au.cisurfboards.com/",
}


def clean(value):
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def normalise_length(value):
    value = clean(value).replace("’", "'").replace('"', "")

    match = re.search(r"([4-9])[\'’]\s*(\d{1,2})", value)

    if not match:
        return None

    return f"{match.group(1)}'{int(match.group(2))}"


def parse_dimensions(text):
    text = clean(BeautifulSoup(text or "", "html.parser").get_text(" "))

    match = re.search(
        r"([4-9]'\s*\d{1,2})\s*x\s*([0-9]+(?:\s+[0-9]+/[0-9]+|[./][0-9]+)?)\s*x\s*([0-9]+(?:\s+[0-9]+/[0-9]+|[./][0-9]+)?)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None, None, None

    return (
        normalise_length(match.group(1)),
        clean(match.group(2)),
        clean(match.group(3)),
    )


def parse_volume(text):
    text = BeautifulSoup(text or "", "html.parser").get_text(" ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", "", text)

    match = re.search(r"Volume:([0-9]+(?:\.[0-9]+)?)L?", text, re.IGNORECASE)

    if not match:
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*L\b", text, re.IGNORECASE)

    if not match:
        return None

    try:
        return float(match.group(1))
    except Exception:
        return None


def detect_fin_setup(value):
    lower = clean(value).lower()

    if "futures" in lower:
        return "Futures"

    if "fcs" in lower:
        return "FCS II"

    return None


def detect_construction(value):
    lower = clean(value).lower()

    if "spine-tek" in lower or "spinetek" in lower:
        return "Spine-Tek"

    if "ect" in lower or "carbon" in lower:
        return "ECT-Carbon"

    if "pu" in lower:
        return "PU"

    if "eps" in lower:
        return "EPS"

    return None


def normalise_model_name(title):
    title = clean(title)

    value = re.sub(r"^[4-9]['’]\s*\d{1,2}\s*", "", title)
    value = re.sub(r"\s*-\s*(Futures|FCS\s*II?|FCSII|Blue|White|Black|Clear|Tint|Swallow|Squash|Round|Pin|Purple|Yellow|Pink).*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" -")

    lower = value.lower()

    construction_terms = [
        "spinetek",
        "spine-tek",
        "spine tek",
        "ect",
        "carbon",
        "eps",
        "pu",
    ]

    for term in construction_terms:
        lower = lower.replace(term, " ")

    lower = re.sub(r"\s+", " ", lower).strip()

    replacements = {
        "better everyday grom": "better-everyday",
        "better everyday": "better-everyday",
        "happy everyday": "happy-everyday",
        "ci 2.pro grom": "ci-2-pro",
        "ci 2 pro grom": "ci-2-pro",
        "ci 2.pro": "ci-2-pro",
        "ci 2 pro": "ci-2-pro",
        "ci pro step up": "ci-pro-step-up",
        "ci pro": "ci-pro",
        "m23": "m-23",
        "m 23": "m-23",
        "g skate": "g-skate",
        "rocket wide": "rocket-wide",
        "rocket wide squash": "rocket-wide-squash",
        "neck beard 3": "neckbeard-3",
        "neckbeard 3": "neckbeard-3",
        "neck beard 2": "neckbeard-2",
        "neckbeard 2": "neckbeard-2",
        "neck beard": "neckbeard",
        "neckbeard": "neckbeard",
        "fish beard": "fishbeard",
        "fishbeard": "fishbeard",
        "bobby quad": "bobby-quad",
        "ci mid twin": "ci-mid-twin",
        "ci mid": "ci-mid",
        "twin pin": "twin-pin",
        "black beauty": "black-beauty",
        "solution": "solution",
        "mikey february shorty": "mikey-february-shorty",
        "sampler": "sampler",
        "fever": "fever",
        "happy": "happy",
    }

    for key, replacement in replacements.items():
        if key in lower:
            return replacement

    return re.sub(r"[^a-z0-9]+", "-", lower).strip("-")


def product_image(product):
    images = product.get("images") or []

    if images and images[0].get("src"):
        return images[0].get("src")

    image = product.get("image") or {}

    return image.get("src")


def is_board_product(product):
    title = clean(product.get("title"))
    product_type = clean(product.get("product_type"))
    body = clean(product.get("body_html"))

    product_type_lower = product_type.lower()
    combined = f"{title} {product_type} {body}".lower()

    if product_type_lower == "surfboard stock":
        return bool(
            re.search(
                r"[4-9][\'’]\s*\d{1,2}",
                title,
            )
        )

    if product_type_lower == "surfboard model":
        return False

    reject_terms = [
        "tee",
        "shirt",
        "hat",
        "cap",
        "pad",
        "traction",
        "leash",
        "cover",
        "bag",
        "wax",
        "sticker",
        "gift card",
    ]

    if any(term in combined for term in reject_terms):
        return False

    return bool(
        re.search(
            r"[4-9][\'’]\s*\d{1,2}",
            combined,
        )
    )


def main():
    print("")
    print("Building Channel Islands AU manufacturer availability")
    print(f"Source: {SOURCE_URL}")

    response = requests.get(SOURCE_URL, headers=HEADERS, timeout=60)
    response.raise_for_status()

    products = response.json().get("products") or []

    rows = []

    for product in products:
        if not is_board_product(product):
            continue

        title = clean(product.get("title"))
        handle = clean(product.get("handle"))
        body_html = product.get("body_html") or ""

        length, width, thickness = parse_dimensions(f"{title} {body_html}")

        if not length:
            length = normalise_length(title)

        volume = parse_volume(body_html)
        model_name = normalise_model_name(title)
        fin_setup = detect_fin_setup(title)
        construction = detect_construction(f"{title} {body_html}")

        variants = product.get("variants") or [{}]
        variant = variants[0]

        available = bool(variant.get("available"))
        price = variant.get("price")

        try:
            price_amount = float(price) if price is not None else None
        except Exception:
            price_amount = None

        product_url = urljoin(BASE_URL, f"/products/{handle}") if handle else BASE_URL

        rows.append({
            "brandName": BRAND_NAME,
            "modelName": model_name,
            "length": length,
            "width": width,
            "thickness": thickness,
            "volumeLitres": volume,
            "construction": construction,
            "finSetup": fin_setup,
            "stockStatus": "available" if available else "sold_out",
            "isAvailable": available,
            "priceAmount": price_amount,
            "priceCurrency": "AUD",
            "productUrl": product_url,
            "productImageUrl": product_image(product),
            "availabilitySource": "manufacturer_direct",
            "regionCode": REGION_CODE,
            "rawProductTitle": title,
            "source": "ci_au_products_json",
            "scrapedAtUtc": datetime.now(timezone.utc).isoformat(),
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    available_rows = [row for row in rows if row.get("isAvailable")]

    print("")
    print("Channel Islands AU manufacturer availability complete")
    print(f"Rows: {len(rows)}")
    print(f"Available rows: {len(available_rows)}")
    print(f"Output: {OUTPUT_FILE}")

    if not rows:
        raise SystemExit("No Channel Islands manufacturer availability rows built")


if __name__ == "__main__":
    main()
