import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.canonical_catalogue_guardrails import (
    append_rejected_products_audit,
    filter_catalogue_rows,
)


BRAND = "Album"
BASE_URL = "https://albumsurf.com"
MODELS_PAGE = "https://albumsurf.com/pages/board-models"

OUTPUT_FILE = Path("scrapers/brands/album/output/album_master_catalogue_clean.json")
REPORT_FILE = Path("scrapers/brands/album/output/album_master_catalogue_clean_report.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


def clean(value):
    value = str(value or "")
    value = value.replace("”", '"').replace("“", '"')
    value = value.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", value).strip()


def normalise_url(url):
    return url.split("?")[0].rstrip("/")


def parse_dimension_line(line):
    line = clean(line)

    pattern = (
        r"(?P<length>\d+'\s*\d{1,2}\"?)\s*x\s*"
        r"(?P<width>\d+(?:\s+\d+/\d+|(?:\.\d+)?)\"?)\s*x\s*"
        r"(?P<thickness>\d+(?:\s+\d+/\d+|(?:\.\d+)?)\"?)"
    )

    match = re.search(pattern, line)

    if not match:
        return None

    return {
        "length": clean(match.group("length")).replace('"', ""),
        "width": clean(match.group("width")).replace('"', ""),
        "thickness": clean(match.group("thickness")).replace('"', ""),
    }


def parse_volume(line):
    match = re.search(r"(?P<volume>\d+(?:\.\d+)?)\s*(?:l|liters?|litres?)\b", line, flags=re.IGNORECASE)

    if not match:
        return None

    return float(match.group("volume"))


SIZE_BLOCK_RE = re.compile(
    r"(?P<length>\d+'\s*\d{1,2})\"?\s*x\s*"
    r"(?P<width>\d+(?:\.\d+|\s+\d+/\d+)?)\"?\s*x\s*"
    r"(?P<thickness>\d+(?:\.\d+|\s+\d+/\d+)?)\"?"
    r"(?:\s*[\(/-]?\s*(?P<volume>\d+(?:\.\d+)?)\s*(?:l|liters?|litres?)\)?)?",
    flags=re.IGNORECASE,
)


def discover_candidate_pages():
    response = requests.get(MODELS_PAGE, headers=HEADERS, timeout=(10, 30))
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    urls = set()

    for a in soup.find_all("a", href=True):
        full_url = normalise_url(urljoin(BASE_URL, a.get("href")))

        if not full_url.startswith(BASE_URL):
            continue

        if "/collections/" not in full_url:
            continue

        bad_terms = [
            "apparel",
            "beach",
            "books",
            "bicycle",
            "fins",
            "footwear",
            "art",
            "skincare",
            "soft-tops",
            "accessories",
            "used-boards",
            "new-boards",
        ]

        if any(term in full_url.lower() for term in bad_terms):
            continue

        urls.add(full_url)

    canonicalised = {}

    for url in urls:

        slug = url.split("/collections/")[-1]

        canonical_slug = slug
        canonical_slug = canonical_slug.replace("-concept", "")
        canonical_slug = canonical_slug.replace("-1", "")

        existing = canonicalised.get(canonical_slug)

        if existing is None:
            canonicalised[canonical_slug] = url
            continue

        existing_score = 0
        new_score = 0

        if "-concept" not in existing:
            existing_score += 10

        if "-1" not in existing:
            existing_score += 5

        if "-concept" not in url:
            new_score += 10

        if "-1" not in url:
            new_score += 5

        if new_score > existing_score:
            canonicalised[canonical_slug] = url

    return sorted(canonicalised.values())


def normalise_model_name(value):
    value = clean(value)
    value = re.sub(r"\s+[–-]\s+Album Surf$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+Album Surf$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+Model$", "", value, flags=re.IGNORECASE)
    aliases = {
        "D'Boa": "D'boa",
        "Vb Secret Menu": "VBSM",
    }
    return aliases.get(clean(value), clean(value))


def extract_model_name(soup, url):
    slug_name = model_name_from_url(url)
    title = normalise_model_name(soup.title.get_text(" ", strip=True) if soup.title else "")
    if slug_name and title and title.lower().startswith(slug_name.lower()):
        return slug_name
    if title and title != "404 Not Found":
        return title

    for selector in ["h1", ".product__title", ".product-single__title"]:
        node = soup.select_one(selector)
        if node:
            value = normalise_model_name(node.get_text(" ", strip=True))
            if slug_name and value and value.lower().startswith(slug_name.lower()):
                return slug_name
            if value:
                return value

    return slug_name


def extract_size_rows(model_name, url, source_text, description_text, meta_description):
    rows = []
    seen = set()
    context_snippet = clean(" ".join(part for part in [meta_description, description_text] if part))[:1500]

    for match in SIZE_BLOCK_RE.finditer(source_text):
        volume = match.group("volume")
        if volume is None:
            trailing_text = source_text[match.end():match.end() + 32]
            volume = parse_volume(trailing_text)
        else:
            volume = float(volume)

        dimension_block = {
            "length": clean(match.group("length")),
            "width": clean(match.group("width")),
            "thickness": clean(match.group("thickness")),
        }

        key = (
            dimension_block["length"],
            dimension_block["width"],
            dimension_block["thickness"],
            volume,
        )
        if key in seen:
            continue
        seen.add(key)

        rows.append({
            "brand": BRAND,
            "model_name": model_name,
            "model_family": model_name,
            "board_category": "Surfboard",
            "description": description_text or meta_description or None,
            "official_product_url": url,
            "official_image_url": None,
            "recommended_wave_range": None,
            "recommended_surfer_weight": None,
            "length_feet_inches": dimension_block["length"],
            "width": dimension_block["width"],
            "thickness": dimension_block["thickness"],
            "volume_litres": volume,
            "construction": "Standard",
            "fin_setup": None,
            "tail_shape": None,
            "source_product_title": model_name,
            "source_variant_title": f"{dimension_block['length']} x {dimension_block['width']} x {dimension_block['thickness']} / {volume}L" if volume is not None else f"{dimension_block['length']} x {dimension_block['width']} x {dimension_block['thickness']}",
            "source": url,
            "guardrail_context": context_snippet,
        })

    return rows


def extract_model_page(url):
    response = requests.get(url, headers=HEADERS, timeout=(10, 30))
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    meta_description = clean((soup.select_one('meta[name="description"]') or {}).get("content", ""))
    description_nodes = soup.select(".rte")
    description_text = clean(" ".join(node.get_text(" ", strip=True) for node in description_nodes[:3]))
    main_node = soup.select_one("main")
    main_text = clean(main_node.get_text("\n", strip=True) if main_node else soup.get_text("\n", strip=True))
    text = main_text

    model_name = extract_model_name(soup, url)
    return extract_size_rows(model_name, url, text, description_text, meta_description)


def model_name_from_url(url):
    slug = url.split("/collections/")[-1]
    slug = slug.replace("-concept", "")
    slug = slug.replace("-1", "")
    words = [part for part in slug.split("-") if part]
    if not words:
        return ""
    name = " ".join(word.capitalize() for word in words)
    aliases = {
        "Dboa": "D'boa",
        "Proto A Typical": "ProtoAtypical",
        "Vbsm": "VBSM",
    }
    return aliases.get(name, name)


def build_model_only_row(model_name, url, guardrail_context=None):
    return {
        "brand": BRAND,
        "model_name": model_name,
        "model_family": model_name,
        "board_category": None,
        "description": clean(guardrail_context) or None,
        "official_product_url": url,
        "official_image_url": None,
        "recommended_wave_range": None,
        "recommended_surfer_weight": None,
        "length_feet_inches": None,
        "width": None,
        "thickness": None,
        "volume_litres": None,
        "construction": None,
        "fin_setup": None,
        "tail_shape": None,
        "source_product_title": model_name,
        "source_variant_title": "Model overview",
        "source": url,
        "source_product_type": None,
        "guardrail_context": clean(guardrail_context),
    }


def extract_model_only_context(response_text):
    soup = BeautifulSoup(response_text, "html.parser")
    meta_description = clean((soup.select_one('meta[name="description"]') or {}).get("content", ""))
    description_nodes = soup.select(".rte")
    description_text = clean(" ".join(node.get_text(" ", strip=True) for node in description_nodes[:3]))
    product_blocks = clean(" ".join(node.get_text(" ", strip=True) for node in soup.select(".product-block")[:6]))
    return clean(" ".join(part for part in [meta_description, description_text, product_blocks] if part))[:1500]


def main():
    candidate_urls = discover_candidate_pages()

    all_rows = []
    page_results = []
    failures = []

    for url in candidate_urls:
        try:
            rows = extract_model_page(url)
            if not rows:
                model_name = model_name_from_url(url)
                if model_name:
                    response = requests.get(url, headers=HEADERS, timeout=(10, 30))
                    response.raise_for_status()
                    rows = [build_model_only_row(model_name, url, extract_model_only_context(response.text))]

            page_results.append({
                "url": url,
                "rows": len(rows),
                "model": rows[0]["model_name"] if rows else None,
            })

            all_rows.extend(rows)

            print(url, "=>", len(rows))

        except Exception as exc:
            failures.append({
                "url": url,
                "error": str(exc),
            })
            print(url, "ERROR", exc)

    seen = set()
    deduped = []

    for row in all_rows:
        key = (
            row["model_name"].lower(),
            row["length_feet_inches"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
            row["construction"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    deduped, rejected_rows = filter_catalogue_rows(BRAND, deduped, extra_context_field="guardrail_context")
    append_rejected_products_audit(rejected_rows)
    for row in deduped:
        row.pop("guardrail_context", None)
    deduped.sort(key=lambda row: (row["model_name"], row["volume_litres"] or 0))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report = {
        "brand": BRAND,
        "candidate_pages": len(candidate_urls),
        "catalogue_rows": len(deduped),
        "rejected_rows": len(rejected_rows),
        "models_with_rows": len(set(row["model_name"] for row in deduped)),
        "page_results": page_results,
        "failures": failures,
        "failure_count": len(failures),
        "output_file": str(OUTPUT_FILE),
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("=" * 100)
    print("ALBUM COMPLETE")
    print("=" * 100)
    print("Candidate pages:", len(candidate_urls))
    print("Catalogue rows:", len(deduped))
    print("Models with rows:", report["models_with_rows"])
    print("Failures:", len(failures))


if __name__ == "__main__":
    main()
