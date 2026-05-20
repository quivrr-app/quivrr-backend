import json
import re
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import requests
from pypdf import PdfReader


BRAND_NAME = "DMS Surfboards"
OFFICIAL_URL = "https://www.dmshapes.com"
PDF_URL = "https://www.dmshapes.com/_files/ugd/398c09_4e8935660f45431aa6ff0e46a5b2f1e0.pdf"
OUTPUT_FILE = Path("scrapers/brands/dms/output/dms_master_catalogue_clean.json")

MODEL_RE = re.compile(r"THE\s+([A-Z0-9 \-]+?)\s+MODEL", re.IGNORECASE)
LENGTH_RE = re.compile(r"[4-9][’']\s*\d{1,2}[”\"]?")
VOL_RE = re.compile(r"\d{2}(?:\.\d+)?L")
WIDTH_RE = re.compile(r"(?:1[7-9]|2[0-4])(?:\s+\d{1,2}/\d{1,2})?[”\"]?")
THICK_RE = re.compile(r"(?:1|2|3)(?:\s+\d{1,2}/\d{1,2})?[”\"]?")
TAIL_RE = re.compile(r"TAIL\s+I\s+(.+)", re.IGNORECASE)
FINS_RE = re.compile(r"FINS\s+I\s+(.+)", re.IGNORECASE)


def clean(value):
    value = str(value or "")
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def get_pdf_text_by_page():
    response = requests.get(PDF_URL, timeout=60)
    response.raise_for_status()

    reader = PdfReader(BytesIO(response.content))
    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return pages


def extract_first(regex, text):
    match = regex.search(text or "")
    if not match:
        return None
    return clean(match.group(1))


def normalise_length(value):
    value = clean(value)
    if not value:
        return None
    value = value.replace('"', "")
    value = value.replace(" ", "")
    return value


def strip_quote(value):
    value = clean(value)
    if not value:
        return None
    return value.replace('"', "").strip()


def parse_page(text):
    model_match = MODEL_RE.search(text)
    if not model_match:
        return []

    model = clean(model_match.group(1).title())
    tail = extract_first(TAIL_RE, text)
    fins = extract_first(FINS_RE, text)

    lengths = [normalise_length(x) for x in LENGTH_RE.findall(text)]
    volumes = [float(x.replace("L", "")) for x in VOL_RE.findall(text)]

    after_table = text
    marker = "LENGTH WIDTH THICK"
    if marker in text:
        after_table = text.split(marker, 1)[1]

    widths = [strip_quote(x) for x in WIDTH_RE.findall(after_table)]
    thicks = [strip_quote(x) for x in THICK_RE.findall(after_table)]

    count = min(len(lengths), len(widths), len(thicks), len(volumes))

    rows = []
    for i in range(count):
        rows.append({
            "model": model,
            "length": lengths[i],
            "width": widths[i],
            "thickness": thicks[i],
            "volume_litres": volumes[i],
            "tail_shape": tail,
            "fin_system": fins,
        })

    return rows


def main():
    print("")
    print("Building DMS Surfboards manufacturer catalogue")
    print(f"Source PDF: {PDF_URL}")

    pages = get_pdf_text_by_page()
    rows = []
    seen = set()

    for page_text in pages:
        parsed = parse_page(page_text)

        if not parsed:
            continue

        model = parsed[0]["model"]
        print(f"{model}: {len(parsed)} stock sizes")

        for size in parsed:
            key = (
                size["model"],
                size["length"],
                size["width"],
                size["thickness"],
                size["volume_litres"],
            )

            if key in seen:
                continue

            seen.add(key)

            rows.append({
                "brand": BRAND_NAME,
                "model": size["model"],
                "model_family": size["model"],
                "board_category": "Surfboard",
                "length": size["length"],
                "width": size["width"],
                "thickness": size["thickness"],
                "volume_litres": size["volume_litres"],
                "construction": "Standard",
                "fin_system": size.get("fin_system"),
                "tail_shape": size.get("tail_shape"),
                "official_product_url": OFFICIAL_URL,
                "official_image_url": None,
                "source": PDF_URL,
                "source_product_title": size["model"],
                "source_product_id": None,
                "source_variant_id": None,
                "source_variant_title": None,
                "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
            })

    if not rows:
        raise RuntimeError("No DMS catalogue rows were built")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print("")
    print("DMS catalogue build complete")
    print(f"Models: {len(set(r['model'] for r in rows))}")
    print(f"Rows: {len(rows)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"DMS catalogue build failed: {exc}")
        sys.exit(1)
