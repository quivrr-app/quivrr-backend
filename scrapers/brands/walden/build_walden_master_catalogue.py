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
    html_to_lines,
    html_to_text,
    normalise_length,
    product_url,
    utc_now,
    write_catalogue,
)


BRAND_NAME = "Walden"
BASE_URL = "https://waldensurfboards.com"
SOURCE_PATH = "/products.json"
SOURCE_URL = f"{BASE_URL}{SOURCE_PATH}"
OUTPUT_FILE = Path("scrapers/brands/walden/output/walden_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/walden/output/walden_master_catalogue_clean_report.json")


def _parse_model(title: str) -> tuple[str | None, str | None]:
    length = normalise_length(title)
    model = re.sub(r"^Surftech\s+", "", title, flags=re.IGNORECASE)
    model = re.sub(r"^\d+'\d{1,2}\s+", "", model)
    model = re.sub(r"\s+#?\d{4,6}\b", "", model)
    model = re.sub(r"\b(2024|2025|2026)\b", "", model)
    model = re.sub(r"\b(SOFTOP|TUFLITE|FUSION HD|Wahine Fusion)\b", "", model, flags=re.IGNORECASE)
    model = clean(model)
    return model or None, length


def _construction(title: str, description: str) -> str | None:
    text = f"{title} {description}".lower()
    if "soft top" in text or "softop" in text:
        return "Soft Top"
    if "eps" in text:
        return "EPS"
    if "tuflite" in text:
        return "Tuflite"
    if "fusion" in text:
        return "Fusion HD"
    return None


def main() -> None:
    products = fetch_products(BASE_URL, SOURCE_PATH)
    rows = []
    filtered = 0
    for product in products:
        title = clean(product.get("title"))
        lowered = title.lower()
        if any(token in lowered for token in ["kneeboard", "custom deposit"]):
            continue
        if clean(product.get("product_type")).lower() != "surfboard":
            continue
        model_name, length = _parse_model(title)
        if not model_name or not length:
            continue
        description = html_to_text(product.get("body_html"))
        lines = html_to_lines(product.get("body_html"))
        filtered += 1
        technology_notes = " ".join(
            line for line in lines if any(token in line.lower() for token in ["concave", "hard rails", "soft top", "eps", "tuflite", "fusion", "rocker"])
        ) or None
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
                "length_feet_inches": length,
                "width": None,
                "thickness": None,
                "volume_litres": None,
                "construction": _construction(title, description),
                "fin_setup": "2 + 1" if "2+1" in description or "2 + 1" in description else None,
                "tail_shape": None,
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
