import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BRAND = "Simon Anderson"
BASE_URL = "https://simonandersonsurfboards.com"

START_URL = f"{BASE_URL}/surfboards/"

OUTPUT_DIR = Path("scrapers/brands/simonanderson/output")

CATALOGUE_FILE = OUTPUT_DIR / "simonanderson_master_catalogue_clean.json"
REPORT_FILE = OUTPUT_DIR / "simonanderson_master_catalogue_clean_report.json"
LINKS_FILE = OUTPUT_DIR / "simonanderson_model_links.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


def clean(value):
    value = str(value or "")
    value = value.replace("\u2019", "'")
    value = value.replace("\u2032", "'")
    value = value.replace("\u2033", '"')
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def discover_model_links():
    response = requests.get(
        START_URL,
        headers=HEADERS,
        timeout=60,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = {}
    seen = set()

    for a in soup.find_all("a", href=True):

        href = a.get("href")

        if not href:
            continue

        full_url = urljoin(BASE_URL, href)

        if "/surfboards/" not in full_url:
            continue

        if full_url.rstrip("/") == START_URL.rstrip("/"):
            continue

        slug = full_url.rstrip("/").split("/")[-1]

        if len(slug) < 3:
            continue

        if slug in seen:
            continue

        seen.add(slug)

        model_name = slug.replace("-", " ").title()

        links[slug] = {
            "model": model_name,
            "url": full_url.rstrip("/"),
        }

    rows = list(links.values())

    LINKS_FILE.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return rows


def parse_table(table):

    rows = []

    trs = table.find_all("tr")

    for tr in trs[1:]:

        cells = [
            clean(td.get_text(" ", strip=True))
            for td in tr.find_all(["td", "th"])
        ]

        if len(cells) < 4:
            continue

        length = cells[0]
        width = cells[1]
        thickness = cells[2]
        volume = cells[3]

        if not re.search(r"\d+'\d{1,2}", length):
            continue

        volume_match = re.search(r"\d+(?:\.\d+)?", volume)

        if not volume_match:
            continue

        rows.append({
            "length_feet_inches": length,
            "width": width,
            "thickness": thickness,
            "volume_litres": float(volume_match.group(0)),
        })

    return rows


def build_catalogue():

    print("")
    print("=" * 100)
    print("SIMON ANDERSON CATALOGUE BUILD")
    print("=" * 100)

    model_links = discover_model_links()

    print("")
    print("Models discovered:", len(model_links))

    catalogue = []
    failures = []

    for model in model_links:

        model_name = model["model"]
        product_url = model["url"]

        print("")
        print("Scraping:", model_name)

        try:

            response = requests.get(
                product_url,
                headers=HEADERS,
                timeout=60,
            )

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            tables = soup.find_all("table")

            if not tables:
                failures.append({
                    "model": model_name,
                    "reason": "no tables found",
                    "url": product_url,
                })
                continue

            image = None

            og = soup.find("meta", attrs={"property": "og:image"})

            if og:
                image = og.get("content")

            description = None

            meta = soup.find("meta", attrs={"name": "description"})

            if meta:
                description = clean(meta.get("content"))

            parsed_rows = 0

            for table in tables:

                dimensions = parse_table(table)

                for dimension in dimensions:

                    catalogue.append({
                        "brand": BRAND,
                        "model_name": model_name,
                        "model_family": model_name,
                        "board_category": "Surfboard",
                        "description": description,
                        "official_product_url": product_url,
                        "official_image_url": image,
                        "recommended_wave_range": None,
                        "recommended_surfer_weight": None,
                        "length_feet_inches": dimension["length_feet_inches"],
                        "width": dimension["width"],
                        "thickness": dimension["thickness"],
                        "volume_litres": dimension["volume_litres"],
                        "construction": "PU",
                        "fin_setup": None,
                        "tail_shape": None,
                        "source_product_title": model_name,
                        "source_variant_title": dimension["length_feet_inches"],
                        "source": BASE_URL,
                    })

                    parsed_rows += 1

            print("Rows:", parsed_rows)

        except Exception as exc:

            failures.append({
                "model": model_name,
                "reason": str(exc),
                "url": product_url,
            })

    deduped = []
    seen = set()

    for row in catalogue:

        key = (
            row["model_name"],
            row["length_feet_inches"],
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
            row["model_name"],
            row["length_feet_inches"],
        )
    )

    CATALOGUE_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    REPORT_FILE.write_text(
        json.dumps({
            "brand": BRAND,
            "source": BASE_URL,
            "models": len(set(r["model_name"] for r in deduped)),
            "rows": len(deduped),
            "failures": failures,
            "failure_count": len(failures),
            "output_file": str(CATALOGUE_FILE),
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("=" * 100)
    print("SIMON ANDERSON COMPLETE")
    print("=" * 100)
    print("Models:", len(set(r["model_name"] for r in deduped)))
    print("Rows:", len(deduped))
    print("Failures:", len(failures))
    print("Output:", CATALOGUE_FILE)


if __name__ == "__main__":
    build_catalogue()
