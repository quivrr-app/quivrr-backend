from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

LENGTH_RE = re.compile(
    r"\b([4-9]|1[0-1])\s*(?:'|’|ft|-)\s*(\d{1,2})?(?:\"|”)?(?=\D|$)",
    re.IGNORECASE,
)
DIMENSION_RE = re.compile(
    r"(?P<length>(?:[4-9]|1[0-1])\s*(?:'|’)\s*(?:\d{1,2})?)\s*(?:\"|”)?\s*[xX]\s*"
    r"(?P<width>\d{1,2}(?:\s+\d/\d|(?:\.\d+)?|(?:\s*/\s*\d+)?)?)\s*(?:\"|”)?\s*[xX]\s*"
    r"(?P<thickness>\d(?:\s+\d/\d|(?:\.\d+)?|(?:\s*/\s*\d+)?)?)\s*(?:\"|”)?"
    r"(?:\s*(?:[xX]|\()\s*(?P<volume>\d{2,3}(?:\.\d+)?)\s*[lL]\)?)?",
    re.IGNORECASE,
)
VOLUME_RE = re.compile(r"\b(\d{2,3}(?:\.\d+)?)\s*(?:L|Liters|Litres)\b", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean(value: object) -> str:
    text = str(value or "")
    text = text.replace("”", '"').replace("“", '"')
    text = text.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip()


def clean_title_key(value: object) -> str:
    text = clean(value).lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalise_length(value: object) -> str | None:
    text = clean(value)
    match = LENGTH_RE.search(text)
    if not match:
        return text or None
    inches = match.group(2) or "0"
    return f"{match.group(1)}'{inches}"


def html_to_text(value: object) -> str:
    soup = BeautifulSoup(str(value or ""), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return clean(soup.get_text(" ", strip=True))


def html_to_lines(value: object) -> list[str]:
    soup = BeautifulSoup(str(value or ""), "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    text = soup.get_text("\n", strip=True)
    return [clean(line) for line in text.splitlines() if clean(line)]


def extract_image(product: dict) -> str | None:
    images = product.get("images") or []
    for image in images:
        if isinstance(image, dict) and clean(image.get("src")):
            return clean(image.get("src"))
    image = product.get("image")
    if isinstance(image, dict):
        return clean(image.get("src")) or None
    return None


def fetch_products(base_url: str, path: str = "/products.json", max_pages: int = 40) -> list[dict]:
    products: list[dict] = []
    for page in range(1, max_pages + 1):
        separator = "&" if "?" in path else "?"
        url = f"{base_url.rstrip('/')}{path}{separator}limit=250&page={page}"
        response = requests.get(url, headers=HEADERS, timeout=(10, 60))
        response.raise_for_status()
        payload = response.json()
        page_products = payload.get("products", [])
        if not page_products:
            break
        products.extend(page_products)
        time.sleep(0.2)
    return products


def product_url(base_url: str, handle: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", f"products/{handle}")


def float_or_none(value: object) -> float | None:
    text = clean(value).replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def find_dimension_triplets(text: object) -> list[dict]:
    rows = []
    source = clean(text)
    for match in DIMENSION_RE.finditer(source):
        rows.append(
            {
                "length_feet_inches": normalise_length(match.group("length")),
                "width": clean(match.group("width")).replace('"', ""),
                "thickness": clean(match.group("thickness")).replace('"', ""),
                "volume_litres": float_or_none(match.group("volume")),
            }
        )
    return rows


def find_first_volume(text: object) -> float | None:
    match = VOLUME_RE.search(clean(text))
    if not match:
        return None
    return float_or_none(match.group(1))


def dedupe_rows(rows: Iterable[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        aliases = row.get("aliases") or []
        row["aliases"] = sorted({clean(alias) for alias in aliases if clean(alias)})
        key = (
            clean(row.get("brand_name")),
            clean(row.get("model_name")),
            clean(row.get("length_feet_inches")),
            clean(row.get("width")),
            clean(row.get("thickness")),
            clean(row.get("volume_litres")),
            clean(row.get("construction")),
            clean(row.get("official_product_url")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def write_catalogue(
    *,
    brand_name: str,
    base_url: str,
    source_url: str,
    output_file: Path,
    report_file: Path,
    rows: list[dict],
    products_seen: int,
    filtered_products: int,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    rows = dedupe_rows(rows)
    output_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    report = {
        "brand": brand_name,
        "base_url": base_url,
        "source_url": source_url,
        "products_seen": products_seen,
        "filtered_products": filtered_products,
        "catalogue_rows": len(rows),
        "created_at_utc": utc_now(),
        "output_file": str(output_file),
    }
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
