import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


BRAND_NAME = "Rusty"
BASE_URL = "https://rustysurfboards.eu"
COLLECTION = "surfboards"

OUTPUT_DIR = Path("scrapers/brands/rusty/output")
CATALOGUE_FILE = OUTPUT_DIR / "rusty_master_catalogue_clean.json"
REPORT_FILE = OUTPUT_DIR / "rusty_master_catalogue_clean_report.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(value):
    if not value:
        return None

    soup = BeautifulSoup(value, "html.parser")
    return clean(soup.get_text(" ", strip=True))


def normalise_model(title):
    value = clean(title)

    value = re.sub(r"^Rusty\s+", "", value, flags=re.I)
    value = re.sub(r"\bSurfboard\b", "", value, flags=re.I)
    value = re.sub(r"\bPerformance\b", "", value, flags=re.I)
    value = re.sub(r"\bAlternative\b", "", value, flags=re.I)
    value = re.sub(r"\bHybrid\b", "", value, flags=re.I)
    value = re.sub(r"\bStep\s*up\b", "", value, flags=re.I)
    value = re.sub(r"\bMid\s*Length\b", "", value, flags=re.I)
    value = re.sub(r"\bLongboard\b", "", value, flags=re.I)

    value = re.sub(r"\s+", " ", value).strip()

    return value


def normalise_length(value):
    value = clean(value)

    value = value.replace("''", '"')
    value = value.replace("”", '"')
    value = value.replace("″", '"')
    value = value.replace('"', "")
    value = value.replace("’", "'")
    value = value.replace("`", "'")

    suffixes = [
        "standard",
        "extra",
        "mint",
        "blue",
        "green",
        "light green",
        "pastel green",
    ]

    lowered = value.lower()

    for suffix in suffixes:

        if lowered.endswith(" " + suffix):
            value = value[:-(len(suffix) + 1)]

        elif lowered.endswith(suffix):
            value = value[:-len(suffix)]

    value = clean(value)

    return value


def normalise_fin(value):
    value = clean(value)

    if not value:
        return None

    value = value.replace("FCSII", "FCS II")
    value = value.replace("FCS 2", "FCS II")

    return value


def normalise_construction(value):
    value = clean(value)

    if not value:
        return None

    upper = value.upper()

    if "EPS" in upper:
        return "EPS"

    if "PU" in upper:
        return "PU"

    return value


def fetch_products():
    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/collections/{COLLECTION}/products.json?limit=250&page={page}"
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        response.raise_for_status()

        data = response.json()
        page_products = data.get("products", [])

        if not page_products:
            break

        products.extend(page_products)

        if len(page_products) < 250:
            break

        page += 1

    return products


def get_product_image(product):
    images = product.get("images") or []

    if images:
        return images[0].get("src")

    image = product.get("image") or {}

    if isinstance(image, dict):
        return image.get("src")

    return None


def should_skip_product(product):
    title = clean(product.get("title"))
    handle = clean(product.get("handle"))
    text = f"{title} {handle}".lower()

    skip_terms = [
        "custom",
        "wakesurf",
        "accessory",
        "fin",
        "gift",
        "tee",
        "shirt",
        "hoodie",
        "cap",
        "hat",
        "bag",
    ]

    return any(term in text for term in skip_terms)


def scrape_dimension_table(page, product_url):
    dimensions = {}

    try:
        page.goto(
            f"{product_url}#dimensions",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        page.wait_for_timeout(5000)

        try:
            page.get_by_role("button", name="Accept").click(timeout=3000)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        tables = soup.find_all("table")

        for table in tables:
            for row in table.find_all("tr"):
                cells = [
                    clean(cell.get_text(" ", strip=True))
                    for cell in row.find_all(["th", "td"])
                ]

                if len(cells) < 4:
                    continue

                length = normalise_length(cells[0])

                if not re.match(r"\d+'\d+", length):
                    continue

                try:
                    width = cells[1].replace('"', "")
                    thickness = cells[2].replace('"', "")
                    volume = float(
                        cells[3]
                        .replace("L", "")
                        .replace("l", "")
                        .replace("\xa0", "")
                        .strip()
                    )
                except Exception:
                    continue

                dimensions[length] = {
                    "width": width,
                    "thickness": thickness,
                    "volume_litres": volume,
                }

    except Exception:
        return {}

    return dimensions


def build_catalogue():
    products = fetch_products()

    rows = []
    failures = []

    print("")
    print("=" * 80)
    print("RUSTY EU DIMENSION TABLE BUILD")
    print("=" * 80)
    print("Products seen:", len(products))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for product in products:
            if should_skip_product(product):
                continue

            title = clean(product.get("title"))
            model = normalise_model(title)
            description = strip_html(product.get("body_html"))
            product_url = f"{BASE_URL}/products/{product.get('handle')}"
            image_url = get_product_image(product)

            print("")
            print("Scraping:", model)

            table_dimensions = scrape_dimension_table(page, product_url)

            if not table_dimensions:
                failures.append({
                    "model": model,
                    "reason": "no dimension table found",
                    "product_url": product_url,
                })
                continue

            variants = product.get("variants") or []

            for variant in variants:
                length = normalise_length(variant.get("option1"))
                fin_system = normalise_fin(variant.get("option2"))
                construction = normalise_construction(variant.get("option3"))

                dims = table_dimensions.get(length)

                if not dims:
                    failures.append({
                        "model": model,
                        "length": length,
                        "reason": "length missing from dimension table",
                        "product_url": product_url,
                    })
                    continue

                rows.append({
                    "brand": BRAND_NAME,
                    "model": model,
                    "model_family": model,
                    "board_category": "Surfboard",
                    "description": description,
                    "length": length,
                    "width": dims["width"],
                    "thickness": dims["thickness"],
                    "volume_litres": dims["volume_litres"],
                    "construction": construction,
                    "fin_system": fin_system,
                    "tail_shape": None,
                    "official_product_url": product_url,
                    "official_image_url": image_url,
                    "source": "rustysurfboards.eu/surfboards",
                    "source_product_id": product.get("id"),
                    "source_variant_id": variant.get("id"),
                    "source_product_handle": product.get("handle"),
                    "source_title": title,
                    "is_active": True,
                })

        browser.close()

    seen = set()
    deduped = []

    for row in rows:
        key = (
            row["model"],
            row["length"],
            row["construction"],
            row["fin_system"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    CATALOGUE_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    models = sorted(set(row["model"] for row in deduped))
    constructions = sorted(set(
        row["construction"]
        for row in deduped
        if row.get("construction")
    ))

    REPORT_FILE.write_text(
        json.dumps(
            {
                "brand": BRAND_NAME,
                "source": BASE_URL,
                "collection": COLLECTION,
                "products_seen": len(products),
                "rows": len(deduped),
                "models": len(models),
                "constructions": constructions,
                "failures": failures[:200],
                "failure_count": len(failures),
                "output_file": str(CATALOGUE_FILE),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("=" * 80)
    print("RUSTY COMPLETE")
    print("=" * 80)
    print("Products seen:", len(products))
    print("Models:", len(models))
    print("Rows:", len(deduped))
    print("Constructions:", constructions)
    print("Failures:", len(failures))
    print("Output:", CATALOGUE_FILE)
    print("Report:", REPORT_FILE)


if __name__ == "__main__":
    build_catalogue()
