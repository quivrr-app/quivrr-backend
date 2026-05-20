import json
import re
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
import numpy as np
from rapidocr_onnxruntime import RapidOCR


BRAND_NAME = "Pukas"
BASE_URL = "https://pukassurf.com"
SEED_URLS = [
    "https://pukassurf.com/en/surfboards/",
    "https://pukassurf.com/en/surfboards/pukas-beachy-mood/",
]
OUTPUT_FILE = Path("scrapers/brands/pukas/output/pukas_master_catalogue_clean.json")
DEBUG_DIR = Path("scrapers/brands/pukas/output/debug_charts")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

ocr = RapidOCR()


def clean(value):
    value = str(value or "")
    value = value.replace("’", "'").replace("‘", "'")
    value = value.replace("″", '"').replace("”", '"').replace("“", '"')
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def get_html(url):
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return response.text


def download_image(url):
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()

    image = Image.open(BytesIO(response.content)).convert("RGB")
    return image


def discover_urls():
    urls = set()

    for seed in SEED_URLS:
        try:
            html = get_html(seed)
        except Exception:
            continue

        soup = BeautifulSoup(html, "html.parser")

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].split("?")[0].strip()
            url = urljoin(BASE_URL, href)
            parsed = urlparse(url)

            if parsed.netloc != "pukassurf.com":
                continue

            if not parsed.path.startswith("/en/surfboards/"):
                continue

            slug = parsed.path.rstrip("/").split("/")[-1]

            if not slug or slug == "surfboards":
                continue

            urls.add(url)

    return sorted(urls)


def extract_title(soup, fallback_url):
    meta = soup.find("meta", property="og:title")

    if meta and meta.get("content"):
        title = clean(meta["content"])

        if title:
            title = title.replace("| Pukas Surf", "").strip()
            return title

    heading = soup.find(["h1", "h2"])

    if heading:
        title = clean(heading.get_text(" ", strip=True))

        if title:
            return title

    slug = fallback_url.rstrip("/").split("/")[-1]
    return clean(slug.replace("-", " ").title())


def extract_main_image(soup):
    meta = soup.find("meta", property="og:image")

    if meta and meta.get("content"):
        return clean(meta["content"])

    image = soup.find("img")

    if image and image.get("src"):
        return urljoin(BASE_URL, image["src"])

    return None


def find_chart_images(soup, page_url):
    urls = []

    for image in soup.find_all("img"):
        src = image.get("src") or image.get("data-src") or image.get("data-lazy-src")
        alt = clean(image.get("alt")) or ""
        src_text = src or ""

        combined = f"{src_text} {alt}".lower()

        if not src:
            continue

        if "size" in combined and "chart" in combined:
            urls.append(urljoin(page_url, src))

    deduped = []
    seen = set()

    for url in urls:
        if url in seen:
            continue

        seen.add(url)
        deduped.append(url)

    return deduped


def centre(box):
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def normalise_length(value):
    value = clean(value)

    if not value:
        return None

    value = value.replace('"', "")
    value = value.replace(" ", "")

    match = re.search(r"([4-9]'\d{1,2})", value)

    if not match:
        return None

    return match.group(1)


def normalise_decimal(value):
    value = clean(value)

    if not value:
        return None

    value = value.replace('"', "")
    value = value.replace("L", "")
    value = value.replace("l", "")
    value = value.replace(".", ".", 1)

    match = re.search(r"\d{1,2}(?:\.\d{1,2})?", value)

    if not match:
        return None

    return match.group(0)


def parse_ocr_chart(image):
    result, _ = ocr(np.array(image))

    if not result:
        return []

    cells = []

    for item in result:
        box, text, score = item
        text = clean(text)

        if not text:
            continue

        x, y = centre(box)

        cells.append({
            "text": text,
            "x": x,
            "y": y,
            "score": float(score),
        })

    cells.sort(key=lambda cell: (cell["y"], cell["x"]))

    rows = []

    for cell in cells:
        lower = cell["text"].lower()

        if lower in {"length", "width", "thickness", "litres", "liters"}:
            continue

        placed = False

        for row in rows:
            if abs(row["y"] - cell["y"]) <= 18:
                row["cells"].append(cell)
                row["y"] = (row["y"] + cell["y"]) / 2
                placed = True
                break

        if not placed:
            rows.append({
                "y": cell["y"],
                "cells": [cell],
            })

    parsed = []

    for row in rows:
        ordered = sorted(row["cells"], key=lambda cell: cell["x"])
        values = [cell["text"] for cell in ordered]

        joined = " ".join(values)

        length = None
        width = None
        thickness = None
        volume = None

        if len(values) >= 4:
            length = normalise_length(values[0])
            width = normalise_decimal(values[1])
            thickness = normalise_decimal(values[2])
            volume = normalise_decimal(values[3])

        if not all([length, width, thickness, volume]):
            match = re.search(
                r"([4-9]'\s*\d{1,2})\s+"
                r"(\d{1,2}(?:\.\d{1,2})?)\s+"
                r"(\d(?:\.\d{1,2})?)\s+"
                r"(\d{2}(?:\.\d{1,2})?)",
                joined,
            )

            if match:
                length = normalise_length(match.group(1))
                width = match.group(2)
                thickness = match.group(3)
                volume = match.group(4)

        if not all([length, width, thickness, volume]):
            continue

        try:
            volume_float = float(volume)
        except Exception:
            continue

        parsed.append({
            "length": length,
            "width": width,
            "thickness": thickness,
            "volume_litres": volume_float,
        })

    deduped = []
    seen = set()

    for row in parsed:
        key = (
            row["length"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    return deduped


def main():
    print("")
    print("Building Pukas manufacturer catalogue")

    product_urls = discover_urls()
    print(f"Candidate product URLs discovered: {len(product_urls)}")

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    seen = set()

    for url in product_urls:
        try:
            html = get_html(url)
        except Exception as exc:
            print(f"Skipped {url}: {exc}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        model = extract_title(soup, url)
        image = extract_main_image(soup)
        chart_urls = find_chart_images(soup, url)

        if not chart_urls:
            print(f"No size chart images: {model}")
            continue

        sizes = []

        for chart_url in chart_urls:
            try:
                chart_image = download_image(chart_url)
            except Exception as exc:
                print(f"Skipped chart for {model}: {exc}")
                continue

            safe_model = re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_").lower()
            chart_path = DEBUG_DIR / f"{safe_model}.png"
            chart_image.save(chart_path)

            sizes.extend(parse_ocr_chart(chart_image))

        if not sizes:
            print(f"No OCR size rows: {model}")
            continue

        print(f"{model}: {len(sizes)} stock sizes")

        for size in sizes:
            key = (
                model,
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
                "model": model,
                "model_family": model,
                "board_category": "Surfboard",
                "length": size["length"],
                "width": size["width"],
                "thickness": size["thickness"],
                "volume_litres": size["volume_litres"],
                "construction": "PU",
                "fin_system": None,
                "tail_shape": None,
                "official_product_url": url,
                "official_image_url": image,
                "source": url,
                "source_product_title": model,
                "source_product_id": None,
                "source_variant_id": None,
                "source_variant_title": None,
                "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
            })

        time.sleep(0.25)

    if not rows:
        raise RuntimeError("No Pukas catalogue rows were built")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print("")
    print("Pukas catalogue build complete")
    print(f"Models: {len(set(r['model'] for r in rows))}")
    print(f"Rows: {len(rows)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Pukas catalogue build failed: {exc}")
        sys.exit(1)
