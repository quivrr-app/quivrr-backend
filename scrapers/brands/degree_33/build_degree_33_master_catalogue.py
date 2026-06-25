from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapers.brands.common_us_shopify_catalogue import (
    clean,
    extract_image,
    fetch_products,
    find_dimension_triplets,
    find_first_volume,
    html_to_lines,
    html_to_text,
    normalise_length,
    product_url,
    utc_now,
    write_catalogue,
)


BRAND_NAME = "Degree 33"
BASE_URL = "https://degree33surfboards.com"
SOURCE_PATH = "/collections/surfboards/products.json"
SOURCE_URL = f"{BASE_URL}{SOURCE_PATH}"
OUTPUT_FILE = Path("scrapers/brands/degree_33/output/degree_33_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/degree_33/output/degree_33_master_catalogue_clean_report.json")


def _model_from_tags_and_title(title: str, tags: list[str]) -> str:
    for tag in tags:
        match = re.search(r"meta-related-collection-([a-z0-9-]+)-related-items", tag)
        if match:
            slug = match.group(1).replace("-", " ")
            return clean(slug).title()
    model = re.sub(r"^\d+'\d{1,2}\"?\s*", "", title)
    model = re.sub(r"\bSurfboard\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\b(Closeout|Used)\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\([^)]*\)", "", model)
    model = re.sub(r"\b(Aqua|Blue|Gray|Grey|Sage|Black|Red|Coral)\s+(Rail|Dip|Resin Tint)\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\bwith\s+[A-Za-z ]+\b", "", model, flags=re.IGNORECASE)
    return clean(model).title()


def _construction(title: str, description: str) -> str | None:
    text = f"{title} {description}".lower()
    if "soft top" in text or "softtop" in text:
        return "Soft Top Epoxy"
    if "nexgen" in text:
        return "NexGen Epoxy"
    if "poly" in text or "fiberglass" in text:
        return "PU"
    if "epoxy" in text:
        return "EPS"
    return None


def main() -> None:
    products = fetch_products(BASE_URL, SOURCE_PATH)
    rows = []
    filtered = 0
    for product in products:
        title = clean(product.get("title"))
        lowered = title.lower()
        if "wall art" in lowered or "used" in lowered:
            continue
        tags = product.get("tags") or []
        if isinstance(tags, str):
            tags = [clean(tag) for tag in tags.split(",") if clean(tag)]
        if "meta-type-surfboards" not in {clean(tag) for tag in tags}:
            continue
        description = html_to_text(product.get("body_html"))
        model_name = _model_from_tags_and_title(title, tags)
        if not model_name:
            continue
        filtered += 1
        dims = find_dimension_triplets(" ".join(html_to_lines(product.get("body_html"))))
        if not dims:
            length = normalise_length(title)
            if length:
                dims = [{
                    "length_feet_inches": length,
                    "width": None,
                    "thickness": None,
                    "volume_litres": find_first_volume(description),
                }]
        technology_notes = " ".join(
            line for line in html_to_lines(product.get("body_html"))
            if not re.search(r"\d+'\d{1,2}|liters?", line, flags=re.I)
        ) or None
        for dim in dims:
            rows.append(
                {
                    "brand_name": BRAND_NAME,
                    "model_name": model_name,
                    "model_family": model_name,
                    "board_category": clean(product.get("product_type")) or "Surfboard",
                    "description": description or None,
                    "technology_notes": technology_notes,
                    "official_product_url": product_url(BASE_URL, clean(product.get("handle"))),
                    "official_image_url": extract_image(product),
                    "official_description_source": SOURCE_URL,
                    "length_feet_inches": dim.get("length_feet_inches"),
                    "width": dim.get("width"),
                    "thickness": dim.get("thickness"),
                    "volume_litres": dim.get("volume_litres"),
                    "construction": _construction(title, description),
                    "fin_setup": "2 + 1" if "2+1" in description or "2 + 1" in description else ("FCS" if "fcs" in description.lower() else None),
                    "tail_shape": "Squash" if "squash tail" in description.lower() else None,
                    "aliases": [model_name, clean(product.get("vendor"))],
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
