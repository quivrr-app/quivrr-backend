import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BRAND_NAME = "Lost"
BASE_URLS = [
    "https://lostsurfboards.net/product-category/surfboards/",
    "https://lostsurfboards.net/boards/",
    "https://lostsurfboards.net/surfboards/",
]

CONSTRUCTION_COLLECTIONS = {
    "LightSpeed": "https://lostsurfboards.com.au/collections/lightspeed",
    "Black Sheep": "https://lostsurfboards.com.au/collections/black-sheep",
    "Lib Tech": "https://lostsurfboards.com.au/collections/lib-tech",
}

OUTPUT_DIR = Path("scrapers/brands/lost/output")
BOARD_URLS_FILE = OUTPUT_DIR / "lost_board_urls.json"
CONSTRUCTION_MATRIX_FILE = OUTPUT_DIR / "lost_construction_matrix.json"
CATALOGUE_FILE = OUTPUT_DIR / "lost_master_catalogue_clean.json"
REPORT_FILE = OUTPUT_DIR / "lost_master_catalogue_clean_report.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}

SKIP_TERMS = [
    "/product-category/",
    "/category/",
    "/tag/",
    "/cart",
    "/checkout",
    "/account",
    "/technology",
    "/team",
    "/blog",
    "/video",
    "/videos",
    "/news",
    "/dealer",
    "/retailer",
    "/contact",
]


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def title_from_slug(url):
    slug = url.rstrip("/").split("/")[-1]
    slug = slug.replace("-", " ")
    return clean(slug.title())


def normalise_model_name(value):
    value = clean(value)

    value = re.sub(r"\bLib\s*Tech\b", "", value, flags=re.I)
    value = re.sub(r"\bLight\s*Speed\s*II\b", "", value, flags=re.I)
    value = re.sub(r"\bLightSpeed\s*II\b", "", value, flags=re.I)
    value = re.sub(r"\bLightspeed\s*II\b", "", value, flags=re.I)
    value = re.sub(r"\bLightSpeed\b", "", value, flags=re.I)
    value = re.sub(r"\bLightspeed\b", "", value, flags=re.I)
    value = value.replace("’", "'")
    value = value.replace("Formula-1", "Formula 1")
    value = value.replace("El Patroń", "El Patron")

    replacements = {
        "Rnf": "RNF",
        "Hp": "HP",
        "Xl": "XL",
        "Mr": "MR",
        "Ka": "KA",
        "F1": "F1",
        "3 0": "3.0",
        "2 0": "2.0",
    }

    for old, new in replacements.items():
        value = re.sub(rf"\b{old}\b", new, value)

    value = value.replace("[", "").replace("]", "")
    value = value.replace("Sub Driver", "Sub-Driver")
    value = value.replace("Puddle Jummper", "Puddle Jumper")
    value = value.replace("Sabotaj", "Sabo Taj")

    value = re.sub(r"[-_/]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return clean(value)


def normalise_collection_model_name(value):
    value = clean(value)

    value = re.sub(r"\bLost\b", "", value, flags=re.I)
    value = re.sub(r"\bSurfboards?\b", "", value, flags=re.I)
    value = re.sub(r"\bLightSpeed\s*II\b", "", value, flags=re.I)
    value = re.sub(r"\bLightSpeed\b", "", value, flags=re.I)
    value = re.sub(r"\bBlack Sheep\b", "", value, flags=re.I)
    value = re.sub(r"\bLib Tech\b", "", value, flags=re.I)
    value = re.sub(r"\bPU\b", "", value, flags=re.I)
    value = re.sub(r"\bEpoxy\b", "", value, flags=re.I)

    value = re.sub(r"[-|_/]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return normalise_model_name(value)


def fetch(url):
    response = requests.get(url, headers=HEADERS, timeout=(10, 30))
    response.raise_for_status()
    return response


def discover_board_urls():
    all_links = set()

    for url in BASE_URLS:
        response = fetch(url)
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            full_url = urljoin(response.url, href).split("?")[0]
            lowered = full_url.lower()

            if "lostsurfboards.net/surfboards/" not in lowered:
                continue

            if lowered.rstrip("/") == "https://lostsurfboards.net/surfboards":
                continue

            if any(skip in lowered for skip in SKIP_TERMS):
                continue

            all_links.add(full_url.rstrip("/") + "/")

    urls = sorted(all_links)

    BOARD_URLS_FILE.write_text(
        json.dumps(urls, indent=2),
        encoding="utf-8",
    )

    return urls


def discover_construction_matrix():
    matrix = {}

    for construction, url in CONSTRUCTION_COLLECTIONS.items():
        response = fetch(url)
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            full_url = urljoin(response.url, href).split("?")[0]
            text = clean(link.get_text(" ", strip=True))

            if not text:
                continue

            lowered_url = full_url.lower()

            if "/products/" not in lowered_url and "/collections/" not in lowered_url:
                continue

            if any(skip in lowered_url for skip in [
                "/cart",
                "/account",
                "/checkout",
                "/policies",
                "/pages",
                "/blogs",
            ]):
                continue

            model = normalise_collection_model_name(text)

            if not model or len(model) < 3:
                continue

            if model.lower() in [
                "view",
                "view all",
                "quick view",
                "add to cart",
                "sale",
                "sold out",
                "skip to content",
                "proformance",
            ]:
                continue

            matrix.setdefault(model.lower(), {
                "model": model,
                "constructions": set(),
                "sources": [],
            })

            matrix[model.lower()]["constructions"].add(construction)
            matrix[model.lower()]["sources"].append({
                "construction": construction,
                "source_text": text,
                "source_url": full_url,
                "collection_url": url,
            })

    output = []

    for item in matrix.values():
        output.append({
            "model": item["model"],
            "constructions": sorted(item["constructions"]),
            "sources": item["sources"],
        })

    output = sorted(output, key=lambda row: row["model"].lower())

    CONSTRUCTION_MATRIX_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {row["model"].lower(): row["constructions"] for row in output}


def parse_board_page(url):
    response = fetch(url)
    soup = BeautifulSoup(response.text, "html.parser")
    html = str(soup)

    h1 = soup.find("h1")
    title = normalise_model_name(clean(h1.get_text(" ", strip=True))) if h1 else title_from_slug(url)

    og_desc = soup.find("meta", attrs={"property": "og:description"})
    description = clean(og_desc.get("content")) if og_desc else None

    og_image = soup.find("meta", attrs={"property": "og:image"})
    image_url = og_image.get("content") if og_image else None

    dimensions = []

    dimension_pattern = re.compile(
        r"(\d+[’']\d+)\s*</td>\s*<td[^>]*>\s*([\d\.]+)\s*</td>\s*<td[^>]*>\s*([\d\.]+)\s*</td>\s*<td[^>]*>\s*([\d\.]+)",
        re.I,
    )

    for match in dimension_pattern.finditer(html):
        dimensions.append({
            "length": match.group(1).replace("’", "'"),
            "width": match.group(2),
            "thickness": match.group(3),
            "volume_litres": float(match.group(4)),
        })

    unique_dimensions = []
    seen = set()

    for row in dimensions:
        key = (
            row["length"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique_dimensions.append(row)

    return {
        "model": title,
        "model_family": title,
        "board_category": "Surfboard",
        "description": description,
        "official_product_url": url,
        "official_image_url": image_url,
        "dimensions": unique_dimensions,
    }


def build_catalogue():
    board_urls = discover_board_urls()
    construction_matrix = discover_construction_matrix()

    rows = []
    failures = []

    for index, url in enumerate(board_urls, start=1):
        print(f"[{index}/{len(board_urls)}] {url}")

        try:
            board = parse_board_page(url)

            if not board["dimensions"]:
                failures.append({
                    "url": url,
                    "reason": "no dimensions found",
                    "model": board["model"],
                })
                continue

            compatible_constructions = ["PU"]
            matrix_constructions = construction_matrix.get(board["model"].lower(), [])

            for construction in matrix_constructions:
                if construction not in compatible_constructions:
                    compatible_constructions.append(construction)

            for construction in compatible_constructions:
                for size in board["dimensions"]:
                    rows.append({
                        "brand": BRAND_NAME,
                        "model": board["model"],
                        "model_family": board["model_family"],
                        "board_category": board["board_category"],
                        "description": board["description"],
                        "length": size["length"],
                        "width": size["width"],
                        "thickness": size["thickness"],
                        "volume_litres": size["volume_litres"],
                        "construction": construction,
                        "fin_system": None,
                        "tail_shape": None,
                        "official_product_url": board["official_product_url"],
                        "official_image_url": board["official_image_url"],
                        "source": "lostsurfboards.net",
                        "is_active": True,
                    })

        except Exception as exc:
            failures.append({
                "url": url,
                "reason": str(exc),
                "model": None,
            })

        time.sleep(0.25)

    seen = set()
    deduped = []

    for row in rows:
        key = (
            row["model"],
            row["length"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
            row["construction"],
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    CATALOGUE_FILE.write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    models = sorted(set(row["model"] for row in deduped))
    constructions = sorted(set(row["construction"] for row in deduped))

    REPORT_FILE.write_text(
        json.dumps(
            {
                "brand": BRAND_NAME,
                "board_urls_found": len(board_urls),
                "rows": len(deduped),
                "models": len(models),
                "constructions": constructions,
                "failures": failures,
                "output_file": str(CATALOGUE_FILE),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("=" * 80)
    print("LOST MASTER CATALOGUE COMPLETE")
    print("=" * 80)
    print("Board URLs:", len(board_urls))
    print("Models:", len(models))
    print("Rows:", len(deduped))
    print("Constructions:", constructions)
    print("Failures:", len(failures))
    print("Output:", CATALOGUE_FILE)
    print("Report:", REPORT_FILE)


if __name__ == "__main__":
    build_catalogue()
