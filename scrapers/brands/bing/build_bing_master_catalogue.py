from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapers.brands.common_us_shopify_catalogue import (
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


BRAND_NAME = "Bing"
BASE_URL = "https://bingsurf.com"
SOURCE_PATH = "/products.json"
SOURCE_URL = f"{BASE_URL}{SOURCE_PATH}"
OUTPUT_FILE = Path("scrapers/brands/bing/output/bing_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/bing/output/bing_master_catalogue_clean_report.json")

TITLE_RE = re.compile(r"^(?P<board>\d{4,6})\s+(?P<length>\d+'\d{1,2})\"?\s+(?P<model>.+)$")
SKIP_TERMS = ("wetsuit", "surf suit", "hat", "shirt", "hoodie", "tee", "trunk", "swim")


def _model_from_tags(tags: list[str]) -> str | None:
    skip = {"stock", "bingretail", "ip", "2024", "2025", "2026"}
    for tag in tags:
        key = clean_title_key(tag)
        if not key or key in skip:
            continue
        if "board" in key or "surf" in key:
            continue
        return clean(tag).replace("-", " ").title()
    return None


def _parse_title(title: str, tags: list[str]) -> tuple[str | None, str | None]:
    match = TITLE_RE.match(title)
    if not match:
        return None, None
    length = normalise_length(match.group("length"))
    tagged = _model_from_tags(tags)
    if tagged:
        return tagged, length
    model = clean(match.group("model"))
    model = re.sub(r"\bBOARDROOM COLLECTION\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\bTWIN FIN\b", "", model, flags=re.IGNORECASE)
    return model.title(), length


def _board_category(tags: list[str], title: str) -> str:
    joined = " ".join(tags).lower() + " " + title.lower()
    if "longboard" in joined or "continental" in joined or "spoiler" in joined or "silver spoon" in joined:
        return "Longboard"
    if "fish" in joined:
        return "Fish"
    return "Surfboard"


def main() -> None:
    products = fetch_products(BASE_URL, SOURCE_PATH)
    rows = []
    filtered = 0
    for product in products:
        title = clean(product.get("title"))
        if any(term in title.lower() for term in SKIP_TERMS):
            continue
        if clean(product.get("vendor")) != "Bing Surfboards":
            continue
        if not clean(product.get("product_type")).lower().startswith("surfboards"):
            continue
        tags = product.get("tags") or []
        if isinstance(tags, str):
            tags = [clean(tag) for tag in tags.split(",") if clean(tag)]
        model_name, length = _parse_title(title, tags)
        if not model_name or not length:
            continue
        filtered += 1
        lines = html_to_lines(product.get("body_html"))
        description = html_to_text(product.get("body_html"))
        technology_notes = " ".join(
            line for line in lines if any(token in line.lower() for token in ["stringer", "single box", "2+1", "fin", "concave", "rocker", "rail", "tail"])
        ) or None
        rows.append(
            {
                "brand_name": BRAND_NAME,
                "model_name": model_name,
                "model_family": model_name,
                "board_category": _board_category(tags, title),
                "description": description or None,
                "technology_notes": technology_notes,
                "official_product_url": product_url(BASE_URL, clean(product.get("handle"))),
                "official_image_url": extract_image(product),
                "official_description_source": SOURCE_URL,
                "length_feet_inches": length,
                "width": None,
                "thickness": None,
                "volume_litres": None,
                "construction": None,
                "fin_setup": "Single Box" if "single box" in description.lower() else ("2 + 1" if "2 + 1" in description.lower() else None),
                "tail_shape": None,
                "aliases": [model_name, clean("_".join(tags[:2]))],
                "source_url": SOURCE_URL,
                "source_product_title": title,
                "source_variant_title": "Default Title",
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
