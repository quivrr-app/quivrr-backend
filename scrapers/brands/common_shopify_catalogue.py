import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


SIZE_LINE_RE = re.compile(
    r"(?P<length>[4-9]\s*(?:'|’|ft)\s*\d{1,2}|[4-9]-\d{1,2})"
    r".{0,18}?"
    r"(?P<width>\d{1,2}(?:\s+\d/\d|(?:\.\d+)?|(?:\s*/\s*\d+)?)?)"
    r".{0,18}?"
    r"(?P<thickness>\d(?:\s+\d/\d|(?:\.\d+)?|(?:\s*/\s*\d+)?)?)"
    r".{0,30}?"
    r"(?P<volume>\d{2}(?:\.\d+)?)\s*(?:l|litres|liters)",
    re.IGNORECASE,
)

LENGTH_ONLY_RE = re.compile(r"\b([4-9])\s*(?:'|’|ft|-)\s*(\d{1,2})\b", re.IGNORECASE)
VOLUME_RE = re.compile(r"\b(\d{2}(?:\.\d+)?)\s*(?:l|litres|liters)\b", re.IGNORECASE)

CONSTRUCTION_TERMS = [
    "PU",
    "PE",
    "EPS",
    "Epoxy",
    "Electralite",
    "ElectraLite",
    "FutureFlex",
    "Carbon",
    "Carbon Wrap",
    "Dark Arts",
    "Phantom Phlex",
    "Stringerless",
]

FIN_TERMS = [
    "FCS II",
    "FCS2",
    "FCS",
    "Futures",
    "Future",
    "Twin",
    "Thruster",
    "Quad",
    "5 Fin",
]


def clean(value):
    if value is None:
        return None

    value = str(value)
    value = re.sub(r"\s+", " ", value).strip()

    return value or None


def normalise_length(value):
    value = clean(value)

    if not value:
        return None

    match = LENGTH_ONLY_RE.search(value)

    if not match:
        return value

    return f"{match.group(1)}'{match.group(2)}"


def find_volume(value):
    value = clean(value)

    if not value:
        return None

    numeric_only = re.fullmatch(r"\d{2}(?:\.\d+)?", value)

    if numeric_only:
        try:
            return float(value)
        except ValueError:
            return None

    match = VOLUME_RE.search(value)

    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def find_term(value, terms):
    text = clean(value)

    if not text:
        return None

    lowered = text.lower()

    for term in terms:
        if term.lower() in lowered:
            return term

    return None


def strip_size_noise(title):
    title = clean(title) or ""
    title = SIZE_LINE_RE.sub("", title)
    title = VOLUME_RE.sub("", title)
    title = LENGTH_ONLY_RE.sub("", title)
    title = re.sub(r"\b(FCS II|FCS2|FCS|Futures|Future|Thruster|Quad|Twin|5 Fin)\b", "", title, flags=re.I)
    title = re.sub(r"\b(PU|PE|EPS|Epoxy|Electralite|FutureFlex|Carbon Wrap|Carbon|Dark Arts|Phantom Phlex)\b", "", title, flags=re.I)

    title = re.sub(r"\bx\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\b(new board|used board|factory 2nd|demo)\b", "", title, flags=re.I)
    title = re.sub(r"\b(CA|HI|AU)\s*ID\s*:?\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\bID\s*:?\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\(\s*\d{4,}\s*\)", "", title)

    # Pyzel uses CA and HI as regional stock labels in product titles.
    # These should not become separate model names in the guided search.
    title = re.sub(r"\b(CA|HI|AU)\b$", "", title, flags=re.I)
    title = re.sub(r"\b(CA|HI|AU)\b", "", title, flags=re.I)

    title = re.sub(r"[-|_/]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()

    return title


def request_json(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    return response.json()


def request_text(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    return response.text


def fetch_shopify_products(base_url):
    products = []

    for page in range(1, 40):
        url = f"{base_url.rstrip('/')}/products.json?limit=250&page={page}"
        data = request_json(url)

        page_products = data.get("products", [])

        if not page_products:
            break

        products.extend(page_products)
        time.sleep(0.4)

    return products


def parse_size_lines(text):
    rows = []

    for match in SIZE_LINE_RE.finditer(text or ""):
        rows.append({
            "length": normalise_length(match.group("length")),
            "width": clean(match.group("width")),
            "thickness": clean(match.group("thickness")),
            "volume_litres": find_volume(match.group("volume")),
        })

    return rows


def html_to_text(html):
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return soup.get_text(" ", strip=True)


def build_catalogue(brand_name, base_url, output_file):
    print("")
    print(f"Building {brand_name} manufacturer catalogue")
    print(f"Source: {base_url}")
    print("")

    products = fetch_shopify_products(base_url)

    rows = []
    seen = set()

    for product in products:
        title = clean(product.get("title"))
        handle = clean(product.get("handle"))
        body_html = product.get("body_html") or ""
        body_text = html_to_text(body_html)
        product_url = urljoin(base_url.rstrip("/") + "/", f"products/{handle}") if handle else base_url
        image_url = None

        images = product.get("images") or []

        if images:
            image_url = images[0].get("src")

        product_type = clean(product.get("product_type"))
        tags = product.get("tags") or []
        tags_text = " ".join(tags) if isinstance(tags, list) else str(tags)

        product_context = " ".join([
            title or "",
            product_type or "",
            tags_text or "",
            body_text[:5000],
        ])

        variants = product.get("variants") or []

        for variant in variants:
            variant_title = clean(variant.get("title"))
            variant_context = " ".join([
                title or "",
                variant_title or "",
                body_text[:5000],
            ])

            size_rows = parse_size_lines(variant_context)

            if not size_rows:
                volume = find_volume(variant_context)
                length_match = LENGTH_ONLY_RE.search(variant_context)

                if volume and length_match:
                    size_rows = [{
                        "length": normalise_length(length_match.group(0)),
                        "width": None,
                        "thickness": None,
                        "volume_litres": volume,
                    }]

            for size in size_rows:
                model_name = strip_size_noise(title)
                construction = find_term(variant_context, CONSTRUCTION_TERMS) or find_term(product_context, CONSTRUCTION_TERMS)
                fin_setup = find_term(variant_context, FIN_TERMS) or find_term(product_context, FIN_TERMS)

                key = (
                    brand_name,
                    model_name,
                    size.get("length"),
                    size.get("width"),
                    size.get("thickness"),
                    size.get("volume_litres"),
                    construction,
                    fin_setup,
                )

                if key in seen:
                    continue

                seen.add(key)

                rows.append({
                    "brand": brand_name,
                    "model": model_name,
                    "model_family": model_name,
                    "board_category": product_type,
                    "length": size.get("length"),
                    "width": size.get("width"),
                    "thickness": size.get("thickness"),
                    "volume_litres": size.get("volume_litres"),
                    "construction": construction,
                    "fin_system": fin_setup,
                    "tail_shape": None,
                    "official_product_url": product_url,
                    "official_image_url": image_url,
                    "source": base_url,
                    "source_product_title": title,
                    "source_product_id": product.get("id"),
                    "source_variant_id": variant.get("id"),
                    "source_variant_title": variant_title,
                    "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                    "is_active": True,
                })

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = output_path.with_name(output_path.stem + "_report.json")
    report_path.write_text(
        json.dumps(
            {
                "brand": brand_name,
                "base_url": base_url,
                "products_seen": len(products),
                "catalogue_rows": len(rows),
                "output_file": str(output_path),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Products seen: {len(products)}")
    print(f"Catalogue rows: {len(rows)}")
    print(f"Output: {output_path}")
    print(f"Report: {report_path}")
    print("")

    if len(rows) == 0:
        raise RuntimeError(f"No catalogue rows were built for {brand_name}")

    return rows
