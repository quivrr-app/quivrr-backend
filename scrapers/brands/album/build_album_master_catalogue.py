import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


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
        r"(?P<width>\d+(?:\.\d+)?\"?)\s*x\s*"
        r"(?P<thickness>\d+(?:\.\d+)?\"?)"
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
    match = re.search(r"(?P<volume>\d+(?:\.\d+)?)\s*liters?", line, flags=re.IGNORECASE)

    if not match:
        return None

    return float(match.group("volume"))


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


def extract_model_page(url):
    response = requests.get(url, headers=HEADERS, timeout=(10, 30))
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    if "stock dimensions" not in text.lower():
        return []

    lines = [clean(line) for line in text.splitlines() if clean(line)]

    model_name = None

    for line in lines:
        if "Stock Dimensions" in line:
            model_name = clean(line.replace("Stock Dimensions", ""))
            break

    if not model_name:
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        model_name = clean(title.replace("– Album Surf", "").replace("Album Surf", ""))

    rows = []

    for idx, line in enumerate(lines):
        dim = parse_dimension_line(line)

        if not dim:
            continue

        volume = None

        for lookahead in lines[idx:idx + 4]:
            volume = parse_volume(lookahead)

            if volume is not None:
                break

        if volume is None:
            continue

        rows.append({
            "brand": BRAND,
            "model_name": model_name,
            "model_family": model_name,
            "board_category": "Surfboard",
            "description": None,
            "official_product_url": url,
            "official_image_url": None,
            "recommended_wave_range": None,
            "recommended_surfer_weight": None,
            "length_feet_inches": dim["length"],
            "width": dim["width"],
            "thickness": dim["thickness"],
            "volume_litres": volume,
            "construction": "Standard",
            "fin_setup": None,
            "tail_shape": None,
            "source_product_title": model_name,
            "source_variant_title": f"{dim['length']} x {dim['width']} x {dim['thickness']} / {volume}L",
            "source": url,
        })

    return rows


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


def build_model_only_row(model_name, url):
    return {
        "brand": BRAND,
        "model_name": model_name,
        "model_family": model_name,
        "board_category": "Surfboard",
        "description": None,
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
    }


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
                    rows = [build_model_only_row(model_name, url)]

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

    deduped.sort(key=lambda row: (row["model_name"], row["volume_litres"]))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report = {
        "brand": BRAND,
        "candidate_pages": len(candidate_urls),
        "catalogue_rows": len(deduped),
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
