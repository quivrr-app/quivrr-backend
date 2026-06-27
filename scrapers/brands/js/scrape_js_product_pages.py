import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT_FILE = Path("scrapers/brands/js/output/js_page_catalogue.json")
REPORT_FILE = Path("scrapers/brands/js/output/js_page_catalogue_report.json")

PRODUCT_URLS = [
    "https://jsindustries.com/products/mother-trucker",
    "https://jsindustries.com/products/step-off-performer",
    "https://jsindustries.com/products/forget-me-not-3-step-up",
    "https://jsindustries.com/products/big-horse",
    "https://jsindustries.com/products/golden-child",
    "https://jsindustries.com/products/forget-me-not-3",
    "https://jsindustries.com/products/monsta",
    "https://jsindustries.com/products/schooner",
    "https://jsindustries.com/products/raging-bull",
    "https://jsindustries.com/products/xero-gravity",
    "https://jsindustries.com/products/xero-fusion",
    "https://jsindustries.com/products/el-baron",
    "https://jsindustries.com/products/big-baron",
    "https://jsindustries.com/products/black-baron",
    "https://jsindustries.com/products/bull-run",
    "https://jsindustries.com/products/sub-xero",
    "https://jsindustries.com/products/flame-fish",
    "https://jsindustries.com/products/golden-child-youth",
    "https://jsindustries.com/products/monsta-youth",
    "https://jsindustries.com/products/xero-gravity-youth",
    "https://jsindustries.com/products/black-eagle-2",
    "https://jsindustries.com/products/big-baron-easy-rider-softboard",
    "https://jsindustries.com/products/big-baron-softboard",
    "https://jsindustries.com/products/bull-run-softboard",
    "https://jsindustries.com/products/flame-fish-softboard",
    "https://jsindustries.com/products/golden-child-easy-rider",
    "https://jsindustries.com/products/monsta-easy-rider",
    "https://jsindustries.com/products/xero-gravity-easy-rider",
    "https://jsindustries.com/products/xero-fusion-easy-rider",
    "https://jsindustries.com/products/raging-bull-easy-rider-1",
]


MODEL_BY_SLUG = {
    "mother-trucker": "Mother Trucker",
    "step-off-performer": "Step Off",
    "forget-me-not-3-step-up": "Forget Me Not 3 Step Up",
    "big-horse": "Big Horse",
    "golden-child": "Golden Child",
    "forget-me-not-3": "Forget Me Not 3",
    "monsta": "Monsta",
    "schooner": "Schooner",
    "raging-bull": "Raging Bull",
    "xero-gravity": "Xero Gravity",
    "xero-fusion": "Xero Fusion",
    "el-baron": "El Baron",
    "big-baron": "Big Baron",
    "black-baron": "Black Baron",
    "bull-run": "Bull Run",
    "sub-xero": "Sub Xero",
    "flame-fish": "Flame Fish",
    "golden-child-youth": "Golden Child Youth",
    "monsta-youth": "Monsta Youth",
    "xero-gravity-youth": "Xero Gravity Youth",
    "black-eagle-2": "Black Eagle 2",
    "big-baron-easy-rider-softboard": "Big Baron Easy Rider",
    "big-baron-softboard": "Big Baron Softboard",
    "bull-run-softboard": "Bull Run Softboard",
    "flame-fish-softboard": "Flame Fish Softboard",
    "golden-child-easy-rider": "Golden Child Easy Rider",
    "monsta-easy-rider": "Monsta Easy Rider",
    "xero-gravity-easy-rider": "Xero Gravity Easy Rider",
    "xero-fusion-easy-rider": "Xero Fusion Easy Rider",
    "raging-bull-easy-rider-1": "Raging Bull Easy Rider",
}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://jsindustries.com/",
    "Connection": "close",
}

PARENT_BOARD_TYPES = {
    "Performance": "shortboard",
    "Parent Board": "shortboard",
    "Softboard": "softboard",
    "Summer": "fish",
    "X-Series": "step-up",
    "Youth Series": "grom",
}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def model_from_url(url):
    slug = url.rstrip("/").split("/")[-1]
    return MODEL_BY_SLUG.get(
        slug,
        slug.replace("-", " ").title(),
    )


def normalise_construction(value):
    value = clean(value)

    if not value:
        return None

    upper_value = value.upper()

    if upper_value == "CARBOTUNE":
        return "CarboTune"

    if upper_value.startswith("HYFI"):
        return "HYFI 3.0"

    if upper_value in {"PU", "PE", "EPS"}:
        return upper_value

    if upper_value == "SOFTBOARD":
        return "Softboard"

    return value


def normalise_fin(value):
    value = clean(value)

    if not value:
        return None

    upper_value = value.upper()

    if "FCS" in upper_value:
        return "FCS II"

    if "FUTURES" in upper_value:
        return "Futures"

    return value


def extract_description(soup):
    meta = soup.find("meta", attrs={"name": "description"})

    if meta and meta.get("content"):
        return clean(meta["content"])

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(script.get_text(strip=True))
        except Exception:
            continue

        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            description = clean(item.get("description"))
            if description:
                return description

    return None


def detect_board_category(page_title, description):
    text = f"{clean(page_title)} {clean(description)}".lower()

    if "easy rider" in text or "mid length" in text:
        return "midlength"

    if "softboard" in text:
        return "softboard"

    if "youth" in text or "grom" in text:
        return "grom"

    if "fish" in text:
        return "fish"

    if "step up" in text:
        return "step-up"

    return "shortboard"


def extract_active_product_object(html):
    match = re.search(
        r"window\.customerHub\.activeProduct\s*=\s*(\{.*?\});",
        html,
        re.S,
    )

    if not match:
        return None

    object_text = match.group(1)

    object_text = re.sub(r"(\w+)\s*:", r'"\1":', object_text)
    object_text = re.sub(r",(\s*[}\]])", r"\1", object_text)

    try:
        return json.loads(object_text)
    except Exception:
        return None


def extract_json_array_after_marker(text, marker):
    marker_index = text.find(marker)

    if marker_index == -1:
        return []

    array_start = text.find("[", marker_index)

    if array_start == -1:
        return []

    depth = 0
    in_string = False
    escaped = False
    array_end = None

    for index in range(array_start, len(text)):
        char = text[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                array_end = index + 1
                break

    if array_end is None:
        return []

    try:
        return json.loads(text[array_start:array_end])
    except Exception:
        return []


def extract_embedded_products(html):
    products = extract_json_array_after_marker(html, '"products":[')
    if products:
        return [product for product in products if isinstance(product, dict)]

    products = extract_json_array_after_marker(html, "console.log([")
    return [product for product in products if isinstance(product, dict)]


def parse_dimensions_from_title(title):
    title = clean(title)
    match = re.search(
        r"(?P<length>[4-9]'\d{1,2}(?:\"?\s*1\/2)?)\s*[xX]\s*"
        r"(?P<width>\d{1,2}(?:\s+\d{1,2}\/\d{1,2})?)[\"]?\s*[xX]\s*"
        r"(?P<thickness>\d(?:\s+\d{1,2}\/\d{1,2})?)[\"]?"
        r"(?:\s*-\s*(?P<volume>\d{1,3}(?:\.\d+)?)L)?",
        title,
        re.IGNORECASE,
    )

    if not match:
        return {}

    length = match.group("length").replace('"', "").replace("1/2", " 1/2")
    length = clean(length.replace("  1/2", " 1/2"))

    payload = {
        "length": length,
        "width": clean(match.group("width")),
        "thickness": clean(match.group("thickness")),
        "volume_litres": None,
    }

    if match.group("volume"):
        payload["volume_litres"] = float(match.group("volume"))

    return payload


def fetch_product_html(url, max_attempts=4):
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                url,
                headers=REQUEST_HEADERS,
                timeout=60,
            )
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(min(2 * attempt, 6))

    raise last_error


def parse_model_from_board_title(title):
    text = clean(title)
    text = re.sub(r"\s+\d'\d{1,2}.*$", "", text)
    text = re.sub(r"\s+(?:Round|Squash|Swallow|Pin|Bat),?.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+-\s+ID:.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+\[T\d+\]$", "", text)
    return clean(text)


def construction_from_title(title):
    text = clean(title).upper()

    if "CARBOTUNE" in text:
        return "CarboTune"
    if "HYFI" in text:
        return "HYFI 3.0"
    if "SOFTBOARD" in text:
        return "Softboard"
    if re.search(r"\bPU\b", text):
        return "PU"
    if re.search(r"\bPE\b", text):
        return "PE"
    if re.search(r"\bEPS\b", text):
        return "EPS"
    return None


def fin_from_title(title):
    text = clean(title).upper()

    if "FCS" in text:
        return "FCS II"
    if "FUTURES" in text:
        return "Futures"
    return None


def extract_board_rows(products, fallback_model_name):
    rows = []

    for product in products:
        handle = clean(product.get("handle"))
        title = clean(product.get("title"))

        if not handle or not title or not handle.startswith("sb"):
            continue

        dimensions = parse_dimensions_from_title(title)
        if not dimensions:
            continue

        rows.append(
            {
                "brand": "JS Industries",
                "model": parse_model_from_board_title(title) or fallback_model_name,
                "construction": construction_from_title(title),
                "fin_system": fin_from_title(title),
                "tail_shape": None,
                "product_url": f"https://jsindustries.com/products/{handle}",
                "price": None,
                "available": True,
                "variant_id": None,
                "official_image_url": None,
                "description": None,
                "board_category": None,
                **dimensions,
            }
        )

    return rows


def build_placeholder_row(url, model_name, active_product, description, board_category):
    image_url = None

    if active_product:
        image_url = clean(active_product.get("imageUrl"))

    return {
        "brand": "JS Industries",
        "model": model_name,
        "construction": None,
        "fin_system": None,
        "tail_shape": None,
        "product_url": url,
        "price": None,
        "available": None,
        "variant_id": None,
        "official_image_url": image_url,
        "description": description,
        "board_category": board_category,
        "length": None,
        "width": None,
        "thickness": None,
        "volume_litres": None,
    }


def scrape_product(url):
    print(f"Scraping {url}")

    html = fetch_product_html(url)
    soup = BeautifulSoup(html, "html.parser")

    model_name = model_from_url(url)
    active_product = extract_active_product_object(html) or {}
    embedded_products = extract_embedded_products(html)
    board_rows = extract_board_rows(embedded_products, model_name)
    description = extract_description(soup)
    board_category = detect_board_category(
        active_product.get("name") or model_name,
        description,
    )

    placeholder_row = build_placeholder_row(
        url,
        model_name,
        active_product,
        description,
        board_category,
    )

    for row in board_rows:
        row["official_image_url"] = row["official_image_url"] or placeholder_row["official_image_url"]
        row["description"] = row["description"] or description
        row["board_category"] = row["board_category"] or board_category

    rows = [placeholder_row, *board_rows]

    print(f"  Model: {model_name}")
    print(f"  Embedded products: {len(embedded_products)}")
    print(f"  Size rows: {len(board_rows)}")
    print(f"  Rows: {len(rows)}")

    return rows


def dedupe_rows(rows):
    deduped = {}

    for row in rows:
        key = "|".join(
            [
                row.get("model") or "",
                row.get("construction") or "",
                row.get("fin_system") or "",
                row.get("length") or "",
                row.get("width") or "",
                row.get("thickness") or "",
                str(row.get("volume_litres") or ""),
                row.get("product_url") or "",
            ]
        )
        deduped[key] = row

    return list(deduped.values())


def build_incomplete_error_message(*, failures, expected_models, scraped_models, missing_models):
    return (
        "JS Industries catalogue scrape incomplete. "
        f"Failures={failures} "
        f"ExpectedModels={expected_models} "
        f"ActualModels={scraped_models} "
        f"MissingModels={missing_models}"
    )


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    all_rows = []
    failures = []

    for url in PRODUCT_URLS:
        try:
            rows = scrape_product(url)
            all_rows.extend(rows)
        except Exception as error:
            print(f"Failed {url}: {error}")
            failures.append(
                {
                    "url": url,
                    "model": model_from_url(url),
                    "error": str(error),
                }
            )

    final_rows = dedupe_rows(all_rows)

    OUTPUT_FILE.write_text(
        json.dumps(final_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    scraped_models = sorted({row.get("model") for row in final_rows if row.get("model")})
    expected_models = sorted(set(MODEL_BY_SLUG.values()))
    missing_models = sorted(set(expected_models) - set(scraped_models))
    rows_with_sizes = sum(1 for row in final_rows if row.get("length"))
    model_placeholder_rows = sum(1 for row in final_rows if not row.get("length"))

    report = {
        "rows_scraped": len(all_rows),
        "rows_deduped": len(final_rows),
        "expected_model_count": len(expected_models),
        "scraped_model_count": len(scraped_models),
        "rows_with_sizes": rows_with_sizes,
        "model_placeholder_rows": model_placeholder_rows,
        "missing_models": missing_models,
        "failures": failures,
        "failure_count": len(failures),
        "output_file": str(OUTPUT_FILE),
    }
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nJS page catalogue built")
    print(f"Rows scraped: {len(all_rows)}")
    print(f"Rows deduped: {len(final_rows)}")
    print(f"Rows with sizes: {rows_with_sizes}")
    print(f"Placeholder rows: {model_placeholder_rows}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Report: {REPORT_FILE}")

    if failures or missing_models:
        raise RuntimeError(
            build_incomplete_error_message(
                failures=len(failures),
                expected_models=len(expected_models),
                scraped_models=len(scraped_models),
                missing_models=len(missing_models),
            )
        )


if __name__ == "__main__":
    main()
