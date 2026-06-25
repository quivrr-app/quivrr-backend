from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapers.brands.common_us_shopify_catalogue import (
    HEADERS,
    clean,
    extract_image,
    fetch_products,
    find_dimension_triplets,
    html_to_lines,
    html_to_text,
    product_url,
    utc_now,
    write_catalogue,
)


BRAND_NAME = "Infinity"
BASE_URL = "https://infinitysurf.com"
SOURCE_PATH = "/collections/surfboards/products.json"
SOURCE_URL = f"{BASE_URL}{SOURCE_PATH}"
OUTPUT_FILE = Path("scrapers/brands/infinity/output/infinity_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/infinity/output/infinity_master_catalogue_clean_report.json")


def _model_name(title: str) -> str:
    return clean(title).replace('"', "")


def _page_dimension_rows(handle: str) -> list[dict]:
    response = requests.get(
        product_url(BASE_URL, handle),
        headers=HEADERS,
        timeout=(10, 60),
    )
    response.raise_for_status()
    matches = re.findall(r"Standard Dims:.*?(?=(?:Standard Dims:|\"sku\":|</script>))", response.text, flags=re.IGNORECASE | re.DOTALL)
    dims: list[dict] = []
    for match in matches:
        text = match.encode("utf-8", "ignore").decode("unicode_escape", "ignore")
        dims.extend(find_dimension_triplets(text))
    return dims


def main() -> None:
    products = fetch_products(BASE_URL, SOURCE_PATH)
    rows = []
    filtered = 0
    for product in products:
        if clean(product.get("product_type")).lower() != "surfboards":
            continue
        title = clean(product.get("title"))
        if "credit" in title.lower():
            continue
        description = html_to_text(product.get("body_html"))
        model_name = _model_name(title)
        dims = find_dimension_triplets(" ".join(html_to_lines(product.get("body_html"))))
        if not dims:
            dims = _page_dimension_rows(clean(product.get("handle")))
        if not dims:
            continue
        filtered += 1
        technology_notes = " ".join(
            line for line in html_to_lines(product.get("body_html"))
            if "standard dims" not in line.lower() and not re.search(r"\d+'\d{1,2}|liters?", line, flags=re.I)
        ) or None
        for dim in dims:
            rows.append(
                {
                    "brand_name": BRAND_NAME,
                    "model_name": model_name,
                    "model_family": model_name,
                    "board_category": "Surfboard",
                    "description": description or None,
                    "technology_notes": technology_notes,
                    "official_product_url": product_url(BASE_URL, clean(product.get("handle"))),
                    "official_image_url": extract_image(product),
                    "official_description_source": SOURCE_URL,
                    "length_feet_inches": dim.get("length_feet_inches"),
                    "width": dim.get("width"),
                    "thickness": dim.get("thickness"),
                    "volume_litres": dim.get("volume_litres"),
                    "construction": None,
                    "fin_setup": None,
                    "tail_shape": None,
                    "aliases": [model_name],
                    "source_url": SOURCE_URL,
                    "source_product_title": title,
                    "source_variant_title": "Standard Dimensions",
                    "last_reviewed_utc": utc_now(),
                }
            )
    write_catalogue(
        brand_name=BRAND_NAME,
        base_url=BASE_URL,
        source_url=SOURCE_URL,
        output_file=OUTPUT_FILE,
        report_file=REPORT_FILE,
        rows=rows,
        products_seen=len(products),
        filtered_products=filtered,
    )


if __name__ == "__main__":
    main()
