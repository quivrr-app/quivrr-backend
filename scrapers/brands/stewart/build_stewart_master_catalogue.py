from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapers.brands.common_us_shopify_catalogue import (
    DIMENSION_RE,
    clean,
    clean_title_key,
    extract_image,
    fetch_products,
    html_to_lines,
    html_to_text,
    normalise_length,
    product_url,
    utc_now,
    write_catalogue,
)


BRAND_NAME = "Stewart"
BASE_URL = "https://stewartsurfboards.com"
SOURCE_PATH = "/products.json"
SOURCE_URL = f"{BASE_URL}{SOURCE_PATH}"
OUTPUT_FILE = Path("scrapers/brands/stewart/output/stewart_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/stewart/output/stewart_master_catalogue_clean_report.json")

TITLE_RE = re.compile(
    r"^(?P<length>\d+'\d{1,2})\"?\s+(?P<model>.+?)\s*\((?P<dims>[^)]*)\)\s*(?:B#\d+)?\s*(?P<construction>EPS|POLY|PU)?$",
    re.IGNORECASE,
)
TITLE_DIMS_RE = re.compile(
    r"(?P<length>\d+'\d{1,2})\"?\s*,\s*"
    r"(?P<width>\d{1,2}(?:\s+\d/\d|(?:\.\d+)?|(?:\s*/\s*\d+)?)?)\"?\s*,\s*"
    r"(?P<thickness>\d(?:\s+\d/\d|(?:\.\d+)?|(?:\s*/\s*\d+)?)?)\"?",
    re.IGNORECASE,
)


def _model_from_title(title: str, tags: list[str]) -> tuple[str | None, str | None, str | None, str | None]:
    match = TITLE_RE.match(title)
    if not match:
        return None, None, None, None
    model = clean(match.group("model"))
    dim_match = TITLE_DIMS_RE.search(match.group("dims")) or DIMENSION_RE.search(match.group("dims"))
    width = clean(dim_match.group("width")).replace('"', "") if dim_match else None
    thickness = clean(dim_match.group("thickness")).replace('"', "") if dim_match else None
    return model, normalise_length(match.group("length")), width, thickness


def main() -> None:
    products = fetch_products(BASE_URL, SOURCE_PATH)
    rows = []
    filtered = 0
    for product in products:
        title = clean(product.get("title"))
        vendor = clean(product.get("vendor"))
        if vendor != "Stewart Surfboards":
            continue
        lowered = title.lower()
        if lowered.startswith("used ") or "consignment" in lowered or "trade-in" in lowered:
            continue
        tags = product.get("tags") or []
        if isinstance(tags, str):
            tags = [clean(tag) for tag in tags.split(",") if clean(tag)]
        if "stock" not in {clean_title_key(tag) for tag in tags}:
            continue
        model_name, length, width, thickness = _model_from_title(title, tags)
        if not model_name or not length:
            continue
        filtered += 1
        description = html_to_text(product.get("body_html"))
        lines = html_to_lines(product.get("body_html"))
        technology_notes = " ".join(
            line for line in lines if any(token in line.lower() for token in ["concave", "rail", "hull", "2 + 1", "futures", "fin", "rocker"])
        ) or None
        construction = "EPS" if "eps" in title.lower() or "eps" in description.lower() else ("PU" if "poly" in title.lower() or "poly" in description.lower() else None)
        board_category = "Longboard" if "longboards" in {clean_title_key(tag) for tag in tags} else "Surfboard"
        rows.append(
            {
                "brand_name": BRAND_NAME,
                "model_name": model_name,
                "model_family": model_name,
                "board_category": board_category,
                "description": description or None,
                "technology_notes": technology_notes,
                "official_product_url": product_url(BASE_URL, clean(product.get("handle"))),
                "official_image_url": extract_image(product),
                "official_description_source": SOURCE_URL,
                "length_feet_inches": length,
                "width": width,
                "thickness": thickness,
                "volume_litres": None,
                "construction": construction,
                "fin_setup": "2 + 1" if "2 + 1" in description or "2+1" in description else None,
                "tail_shape": "Rounded Pin" if "rounded pin" in description.lower() else None,
                "aliases": [model_name] + [clean(tag) for tag in tags if clean(tag) and clean(tag).lower() == model_name.lower()],
                "source_url": SOURCE_URL,
                "source_product_title": title,
                "source_variant_title": clean((product.get("variants") or [{}])[0].get("title")),
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
