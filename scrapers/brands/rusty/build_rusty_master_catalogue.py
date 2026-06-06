import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BRAND_NAME = "Rusty"
BASE_URL = "https://rustysurfboards.com"

SOURCE_COLLECTIONS = [
    "all-boards",
    "all-shortboards",
    "step-ups",
    "all-alternatives",
    "longboards",
    "mid-lengths",
    "all-big-boards",
]

BLOCKED_COLLECTION_SLUGS = {
    "all-boards",
    "all-shortboards",
    "step-ups",
    "all-alternatives",
    "longboards",
    "mid-lengths",
    "all-big-boards",
    "shortboards",
    "alternatives",
    "big-boards",
    "grom-surfboards",
    "wakesurf-boards",
    "wake-in-stock",
    "wakesurf-fins",
    "wake-accessories",
    "in-stock",
    "factory-seconds",
    "rdm-consignment",
    "accessories",
    "fins",
    "r-tired",
    "custom",
    "hair",
}

BLOCKED_SLUG_PARTS = [
    "wake",
    "accessor",
    "fin",
    "stock",
    "factory",
    "second",
    "consignment",
    "sale",
    "custom",
]

OUTPUT_DIR = Path("scrapers/brands/rusty/output")
CATALOGUE_FILE = OUTPUT_DIR / "rusty_master_catalogue_clean.json"
REPORT_FILE = OUTPUT_DIR / "rusty_master_catalogue_clean_report.json"
MODEL_LINKS_FILE = OUTPUT_DIR / "rusty_model_links.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


def clean(value):
    value = str(value or "")
    value = value.replace("\u2019", "'").replace("\u2018", "'")
    value = value.replace("\u2032", "'").replace("\u2033", '"')
    value = re.sub(r"\s+", " ", value).strip()
    return value


def slug_to_model(slug):
    special = {
        "sd": "SD",
        "sd-rt-re": "SD RT RE",
        "421-fish": "421 Fish",
        "419-fish": "419 Fish",
        "d-min": "D Min",
        "big-d": "Big D",
        "so-fuunnn": "So Fuunnn",
    }

    if slug in special:
        return special[slug]

    return slug.replace("-", " ").title()


def should_skip_slug(slug):
    if slug in BLOCKED_COLLECTION_SLUGS:
        return True

    return any(part in slug for part in BLOCKED_SLUG_PARTS)


def discover_model_links():
    links = {}

    for collection in SOURCE_COLLECTIONS:
        url = f"{BASE_URL}/collections/{collection}"

        print("")
        print("Discovering:", url)

        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a.get("href")
            full_url = urljoin(BASE_URL, href)

            if "/collections/" not in full_url:
                continue

            slug = full_url.rstrip("/").split("/")[-1].split("?")[0]

            if not slug:
                continue

            if should_skip_slug(slug):
                continue

            links[slug] = full_url.split("?")[0]

    rows = [
        {
            "model": slug_to_model(slug),
            "slug": slug,
            "url": url,
        }
        for slug, url in sorted(links.items())
    ]

    MODEL_LINKS_FILE.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return rows


def parse_dimension_table(html):
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    dimensions = []

    for table in tables:
        rows = table.find_all("tr")

        for row in rows:
            cells = [
                clean(cell.get_text(" ", strip=True))
                for cell in row.find_all(["th", "td"])
            ]

            if len(cells) < 4:
                continue

            if cells[0].lower() in ["length", "size"]:
                continue

            length = normalise_length(cells[0])

            if not length:
                continue

            width = normalise_decimal_dimension(cells[1])
            thickness = normalise_decimal_dimension(cells[2])
            volume = normalise_volume(cells[3])

            if not width or not thickness or volume is None:
                continue

            dimensions.append({
                "length": length,
                "width": width,
                "thickness": thickness,
                "volume_litres": volume,
            })

    return dimensions


def normalise_length(value):
    value = clean(value)
    value = value.replace('"', "")
    value = value.replace(" ", "")

    match = re.search(r"([4-9])'(\d{1,2})", value)

    if not match:
        return None

    return f"{match.group(1)}'{int(match.group(2))}"


def normalise_decimal_dimension(value):
    value = clean(value)
    value = value.replace('"', "")
    value = value.replace("in", "")
    value = value.strip()

    match = re.search(r"\d+(?:\.\d+)?", value)

    if not match:
        return None

    return match.group(0)


def normalise_volume(value):
    value = clean(value)
    value = value.replace("L", "").replace("l", "").strip()

    match = re.search(r"\d+(?:\.\d+)?", value)

    if not match:
        return None

    return float(match.group(0))


def get_page_description(html):
    soup = BeautifulSoup(html, "html.parser")

    meta = soup.find("meta", attrs={"name": "description"})

    if meta and meta.get("content"):
        return clean(meta.get("content"))

    return None


def get_page_image(html):
    soup = BeautifulSoup(html, "html.parser")

    meta = soup.find("meta", attrs={"property": "og:image"})

    if meta and meta.get("content"):
        return meta.get("content")

    return None


def build_catalogue():
    print("")
    print("=" * 100)
    print("RUSTY CANONICAL MODEL CATALOGUE BUILD")
    print("=" * 100)

    model_links = discover_model_links()

    print("")
    print("Candidate model pages:", len(model_links))

    rows = []
    failures = []

    for model_link in model_links:
        model = model_link["model"]
        url = model_link["url"]

        print("")
        print("Scraping:", model, "=>", url)

        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()

            html = response.text
            dimensions = parse_dimension_table(html)

            if not dimensions:
                failures.append({
                    "model": model,
                    "url": url,
                    "reason": "no dimensions table found",
                })
                continue

            description = get_page_description(html)
            image_url = get_page_image(html)

            for dimension in dimensions:
                rows.append({
                    "brand": BRAND_NAME,
                    "model": model,
                    "model_family": model,
                    "board_category": "Surfboard",
                    "description": description,
                    "length": dimension["length"],
                    "width": dimension["width"],
                    "thickness": dimension["thickness"],
                    "volume_litres": dimension["volume_litres"],
                    "construction": "Standard",
                    "fin_system": None,
                    "tail_shape": None,
                    "official_product_url": url,
                    "official_image_url": image_url,
                    "source": BASE_URL,
                    "source_product_id": None,
                    "source_variant_id": None,
                    "source_product_handle": model_link["slug"],
                    "source_title": model,
                    "is_active": True,
                })

            print("Rows:", len(dimensions))

        except Exception as exc:
            failures.append({
                "model": model,
                "url": url,
                "reason": str(exc),
            })

    seen = set()
    deduped = []

    for row in rows:
        key = (
            row["model"],
            row["length"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    deduped.sort(
        key=lambda row: (
            row["model"],
            row["length"],
            row["volume_litres"] or 0,
        )
    )

    CATALOGUE_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    models = sorted(set(row["model"] for row in deduped))

    REPORT_FILE.write_text(
        json.dumps(
            {
                "brand": BRAND_NAME,
                "source": BASE_URL,
                "source_collections": SOURCE_COLLECTIONS,
                "candidate_model_pages": len(model_links),
                "rows": len(deduped),
                "models": len(models),
                "model_names": models,
                "failures": failures[:200],
                "failure_count": len(failures),
                "output_file": str(CATALOGUE_FILE),
                "model_links_file": str(MODEL_LINKS_FILE),
                "mfa_policy": "disabled_for_au_until_direct_au_manufacturer_availability_exists",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("=" * 100)
    print("RUSTY CANONICAL COMPLETE")
    print("=" * 100)
    print("Candidate model pages:", len(model_links))
    print("Models:", len(models))
    print("Rows:", len(deduped))
    print("Failures:", len(failures))
    print("Output:", CATALOGUE_FILE)
    print("Report:", REPORT_FILE)


if __name__ == "__main__":
    build_catalogue()

