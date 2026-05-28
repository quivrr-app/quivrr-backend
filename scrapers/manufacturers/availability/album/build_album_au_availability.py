import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://albumsurf.com.au/collections/new-boards/products.json?limit=250"
BOARD_MODELS_URL = "https://albumsurf.com.au/pages/board-models"
BASE_URL = "https://albumsurf.com.au"

OUTPUT_FILE = Path(
    "scrapers/manufacturers/availability/output/album/album_au_manufacturer_inventory.json"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://albumsurf.com.au/",
    "X-Shopify-Currency": "AUD",
}

DIMENSION_CACHE = {}
MODEL_COLLECTION_CACHE = {}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalise_model_key(value):
    value = clean(value).lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalise_quote_chars(value):
    return (
        clean(value)
        .replace("’", '"')
        .replace("”", '"')
        .replace("“", '"')
        .replace("′", "'")
        .replace("″", '"')
    )


def normalise_length(value):
    value = normalise_quote_chars(value)

    match = re.search(r"(\d+)'\s*(\d+)", value)

    if not match:
        return None

    return f"{match.group(1)}'{match.group(2)}"


def normalise_decimal(value):
    value = clean(value).replace('"', "")

    if not value:
        return None

    try:
        number = float(value)
    except ValueError:
        return value

    if number.is_integer():
        return str(int(number))

    return str(number).rstrip("0").rstrip(".")


def product_image(product):
    images = product.get("images") or []

    if not images:
        return None

    return images[0].get("src")


def is_board_product(product):
    product_type = clean(product.get("product_type")).lower()
    title = clean(product.get("title")).lower()

    return (
        "surfboard" in product_type
        or "board" in product_type
        or bool(re.search(r"\d+'\s*\d+", title))
    )


def model_name_from_handle(handle):
    value = re.sub(r"^\d+'?\d*[- ]*", "", clean(handle))
    value = re.sub(r"-\d+$", "", value)

    replacements = {
        "plasmic": "Plasmic",
        "lightbender": "Lightbender",
        "twinsman": "Twinsman",
        "protoatypical": "ProtoAtypical",
        "proto-atypical": "ProtoAtypical",
        "freewing": "Freewing",
        "sunstone": "Sunstone",
        "the-end": "The End",
        "bom-dia": "Bom Dia",
        "vb-secret-menu": "VBSM",
        "vbsm": "VBSM",
        "disorder": "Disorder",
        "insanity": "Insanity",
        "moonstone": "Moonstone",
        "fascination": "Fascination",
        "vesper-mini": "Vesper Mini",
        "vesper": "Vesper",
        "veebee-blunt": "Veebee Blunt",
        "veebee": "Veebee",
        "delma": "Delma",
        "bmw": "BMW",
    }

    for key, name in replacements.items():
        if key in value:
            return name

    return value.replace("-", " ").strip().title()


def load_model_collection_map():
    if MODEL_COLLECTION_CACHE:
        return MODEL_COLLECTION_CACHE

    response = requests.get(
        BOARD_MODELS_URL,
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for link in soup.find_all("a", href=True):
        href = clean(link.get("href"))
        label = clean(link.get_text(" ", strip=True))

        if "/collections/" not in href or not label:
            continue

        label = re.sub(
            r"\s+\d+\s+products?$",
            "",
            label,
            flags=re.IGNORECASE,
        )

        key = normalise_model_key(label)

        if not key:
            continue

        if href.startswith("/"):
            href = f"{BASE_URL}{href}"

        MODEL_COLLECTION_CACHE[key] = href

    return MODEL_COLLECTION_CACHE


def resolve_collection_url(model_name):
    model_map = load_model_collection_map()
    model_key = normalise_model_key(model_name)

    alias_map = {
        "protoatypical": "proto a typical",
        "vbsm": "vb secret menu",
        "veebee blunt": "veebee",
        "vesper mini": "vesper",
    }

    candidate_keys = [
        model_key,
        alias_map.get(model_key),
    ]

    for candidate in candidate_keys:
        if candidate and candidate in model_map:
            return model_map[candidate]

    for key, url in model_map.items():
        if model_key and (model_key in key or key in model_key):
            return url

    return None


def parse_dimension_table_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    dimensions = {}

    for row in soup.find_all("tr"):
        cells = [
            normalise_quote_chars(cell.get_text(" ", strip=True))
            for cell in row.find_all(["td", "th"])
        ]

        if len(cells) < 2:
            continue

        size_text = cells[0]
        litres_text = cells[1]

        size_match = re.search(
            r"(?P<length>\d+'\s*\d+)\s*\"?\s*x\s*(?P<width>\d+(?:\.\d+)?)\s*\"?\s*x\s*(?P<thickness>\d+(?:\.\d+)?)",
            size_text,
            re.IGNORECASE,
        )

        litres_match = re.search(
            r"(?P<litres>\d+(?:\.\d+)?)\s*liters?",
            litres_text,
            re.IGNORECASE,
        )

        if not size_match:
            continue

        length = normalise_length(size_match.group("length"))

        if not length:
            continue

        dimensions[length] = {
            "width": normalise_decimal(size_match.group("width")),
            "thickness": normalise_decimal(size_match.group("thickness")),
            "volumeLitres": float(litres_match.group("litres")) if litres_match else None,
        }

    return dimensions


def fetch_dimension_map_for_model(model_name):
    if model_name in DIMENSION_CACHE:
        return DIMENSION_CACHE[model_name]

    url = resolve_collection_url(model_name)

    if not url:
        DIMENSION_CACHE[model_name] = {}
        print(f"No Album model collection URL found for {model_name}")
        return {}

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=60,
        )
        response.raise_for_status()

        dimensions = parse_dimension_table_from_html(response.text)

        if dimensions:
            DIMENSION_CACHE[model_name] = dimensions
            print(f"Dimension table loaded for {model_name}: rows={len(dimensions)}")
            return dimensions

    except Exception as ex:
        print(f"Dimension table fetch failed for {model_name} at {url}: {ex}")

    DIMENSION_CACHE[model_name] = {}
    print(f"No dimension table found for {model_name}")

    return {}


def extract_dimensions(model_name, length):
    dimensions = fetch_dimension_map_for_model(model_name)

    if length in dimensions:
        item = dimensions[length]
        return item.get("width"), item.get("thickness"), item.get("volumeLitres")

    return None, None, None


def main():
    print("")
    print("Building Album AU manufacturer availability")
    print(f"Source: {SOURCE_URL}")

    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()

    products = response.json().get("products") or []

    rows = []
    rows_with_dimensions = 0
    rows_with_litres = 0

    for product in products:
        try:
            if not is_board_product(product):
                continue

            title = clean(product.get("title"))

            if not title:
                continue

            variant = (product.get("variants") or [{}])[0]
            handle = clean(product.get("handle"))
            product_url = f"{BASE_URL}/products/{handle}"

            available = bool(variant.get("available"))
            price = variant.get("price")

            model_name = model_name_from_handle(handle)
            length = normalise_length(title)

            width, thickness, litres = extract_dimensions(model_name, length)

            if width and thickness:
                rows_with_dimensions += 1

            if litres is not None:
                rows_with_litres += 1

            rows.append({
                "brandName": "Album",
                "modelName": model_name,
                "length": length,
                "width": width,
                "thickness": thickness,
                "volumeLitres": litres,
                "construction": None,
                "stockStatus": "available" if available else "sold_out",
                "isAvailable": available,
                "priceAmount": float(price) if price else None,
                "priceCurrency": "AUD",
                "productUrl": product_url,
                "productImageUrl": product_image(product),
                "availabilitySource": "manufacturer_direct",
                "regionCode": "AU",
            })

        except Exception as ex:
            print(f"Failed Album product: {ex}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    available_rows = [
        row for row in rows
        if row.get("isAvailable")
    ]

    print("")
    print("Album AU manufacturer availability complete")
    print(f"Rows: {len(rows)}")
    print(f"Available rows: {len(available_rows)}")
    print(f"Rows with dimensions: {rows_with_dimensions}")
    print(f"Rows with litres: {rows_with_litres}")
    print(f"Output: {OUTPUT_FILE}")

    if not rows:
        raise SystemExit("No Album manufacturer availability rows built")


if __name__ == "__main__":
    main()
