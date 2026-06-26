import json
import re
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://shop-au.cisurfboards.com"

INPUT_LINKS = Path(
    "scrapers/brands/channel_islands/output/ci_canonical_model_links.json"
)

OUTPUT_DIR = Path("scrapers/brands/channel_islands/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "ci_master_catalogue.json"
REPORT_FILE = OUTPUT_DIR / "ci_master_catalogue_report.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)"
}

CONSTRUCTION_TERMS = [
    "PU",
    "ECT",
    "Eco Carbon Tech",
    "Spine-Tek",
    "Spine Tek",
    "Spinetek",
    "Epoxy",
    "EPS",
    "Carbon",
    "Poly",
]

FIN_TERMS = [
    "Futures",
    "FCS II",
    "FCSII",
    "FCS",
    "Single Fin",
    "Twin",
    "Thruster",
    "Quad",
    "2+1",
]

INVALID_MODEL_SLUGS = {
    "gift-card",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def normalise_construction(value: str) -> str | None:
    text = value.lower()

    if "eco carbon tech" in text or "ect" in text:
        return "ECT"

    if (
        "spine-tek" in text
        or "spine tek" in text
        or "spinetek" in text
    ):
        return "Spine-Tek"

    if re.search(r"\bpu\b", text):
        return "PU"

    if "eps" in text:
        return "EPS"

    if "epoxy" in text:
        return "Epoxy"

    if "carbon" in text:
        return "Carbon"

    return None


def normalise_fin(value: str) -> str | None:
    text = value.lower()

    if "fcs ii" in text or "fcsii" in text:
        return "FCS II"

    if "futures" in text:
        return "Futures"

    if "single" in text:
        return "Single Fin"

    if "quad" in text:
        return "Quad"

    if "twin" in text:
        return "Twin"

    if "thruster" in text:
        return "Thruster"

    return None


def extract_json_ld(
    soup: BeautifulSoup,
) -> list[dict[str, Any]]:
    items = []

    for script in soup.find_all(
        "script",
        type="application/ld+json",
    ):
        text = script.get_text(strip=True)

        if not text:
            continue

        try:
            payload = json.loads(text)

            if isinstance(payload, list):
                items.extend(
                    [
                        item
                        for item in payload
                        if isinstance(item, dict)
                    ]
                )

            elif isinstance(payload, dict):
                items.append(payload)

        except Exception:
            continue

    return items


def extract_images(
    soup: BeautifulSoup,
    json_ld_items: list[dict[str, Any]],
) -> list[str]:
    images = []

    for item in json_ld_items:
        image = item.get("image")

        if isinstance(image, str):
            images.append(image)

        elif isinstance(image, list):
            images.extend(
                [
                    value
                    for value in image
                    if isinstance(value, str)
                ]
            )

    for meta_key in ["og:image", "twitter:image"]:
        node = (
            soup.find("meta", property=meta_key)
            or soup.find("meta", attrs={"name": meta_key})
        )

        if node and node.get("content"):
            images.append(node["content"])

    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
        )

        if not src:
            continue

        if src.startswith("//"):
            src = "https:" + src

        elif src.startswith("/"):
            src = BASE_URL + src

        if "logo" not in src.lower():
            images.append(src)

    clean_images = []

    for image in images:
        if image and image not in clean_images:
            clean_images.append(image)

    return clean_images[:12]


def extract_description(
    soup: BeautifulSoup,
    json_ld_items: list[dict[str, Any]],
) -> str:
    for item in json_ld_items:
        description = item.get("description")

        if description:
            return clean_text(str(description))

    meta = soup.find(
        "meta",
        attrs={"name": "description"},
    )

    if meta and meta.get("content"):
        return clean_text(meta["content"])

    return ""


def extract_title(
    soup: BeautifulSoup,
    fallback: str,
) -> str:
    h1 = soup.find("h1")

    if h1:
        return clean_text(
            h1.get_text(" ", strip=True)
        )

    og_title = soup.find(
        "meta",
        property="og:title",
    )

    if og_title and og_title.get("content"):
        return clean_text(og_title["content"])

    return fallback


def extract_dimensions_from_tables(
    soup: BeautifulSoup,
) -> list[dict[str, Any]]:
    dimensions = []
    seen = set()

    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")

        for row in rows:
            cols = [
                clean_text(
                    col.get_text(" ", strip=True)
                )
                for col in row.find_all(["td", "th"])
            ]

            if len(cols) < 4:
                continue

            length = cols[0]
            width = cols[1]
            thickness = cols[2]
            volume = cols[3]

            if "length" in length.lower():
                continue

            volume_match = re.search(
                r"(\d+(?:\.\d+)?)",
                volume,
            )

            if not volume_match:
                continue

            clean_length = (
                length
                .replace("’", "'")
                .replace("‘", "'")
                .replace("´", "'")
                .strip()
            )

            item = {
                "length": clean_length,
                "width": width,
                "thickness": thickness,
                "volume_litres": float(
                    volume_match.group(1)
                ),
            }

            key = (
                item["length"],
                item["width"],
                item["thickness"],
                item["volume_litres"],
            )

            if key not in seen:
                seen.add(key)
                dimensions.append(item)

    return dimensions


def extract_constructions(
    text: str,
) -> list[str]:
    constructions = []

    for term in CONSTRUCTION_TERMS:
        normalised = normalise_construction(term)

        if (
            normalised
            and term.lower() in text.lower()
            and normalised not in constructions
        ):
            constructions.append(normalised)

    return constructions


def extract_fin_setups(
    text: str,
) -> list[str]:
    fins = []

    for term in FIN_TERMS:
        normalised = normalise_fin(term)

        if (
            normalised
            and term.lower() in text.lower()
            and normalised not in fins
        ):
            fins.append(normalised)

    return fins


def model_key(value: str | None) -> str:
    text = clean_text(value)
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\bthe\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def append_unique(values: list[str], value: str | None) -> None:
    if value and value not in values:
        values.append(value)


def construction_from_stock_text(value: str) -> str | None:
    text = value.lower()

    if "pu/pe" in text or "pu pe" in text:
        return "PU"

    if re.search(r"\bpu\b", text):
        return "PU"

    if "spine-tek" in text or "spinetek" in text or "spine tek" in text:
        return "Spine-Tek"

    if "eco carbon tech" in text or "ect" in text:
        return "ECT"

    if "epoxy" in text:
        return "Epoxy"

    if "eps" in text:
        return "EPS"

    return None


def fetch_shopify_products() -> list[dict[str, Any]]:
    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/products.json?limit=250&page={page}"

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=60,
        )

        response.raise_for_status()

        page_products = response.json().get("products", [])

        if not page_products:
            break

        products.extend(page_products)
        page += 1

        if page > 30:
            break

    return products


def build_stock_construction_map(
    model_links: list[dict[str, Any]],
) -> dict[str, list[str]]:
    model_lookup = {}

    for item in model_links:
        slug = item.get("slug")
        model_name = item.get("model_name")

        if not slug:
            continue

        for value in [model_name, slug]:
            key = model_key(value)

            if key:
                model_lookup[key] = slug

    construction_map: dict[str, list[str]] = {}

    for product in fetch_shopify_products():
        product_type = clean_text(product.get("product_type"))

        if product_type.lower() not in {
            "surfboard stock",
            "surfboards",
        }:
            continue

        title = clean_text(product.get("title"))
        handle = clean_text(product.get("handle"))
        tags = [
            clean_text(str(tag))
            for tag in product.get("tags") or []
        ]

        combined = " ".join([title, handle] + tags)

        construction = construction_from_stock_text(combined)

        if not construction:
            continue

        matched_model = None

        for tag in tags:
            key = model_key(tag)

            if key in model_lookup:
                matched_model = model_lookup[key]
                break

        if not matched_model:
            product_key = model_key(title)

            for key, model_name in sorted(
                model_lookup.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            ):
                if key and key in product_key:
                    matched_model = model_name
                    break

        if not matched_model:
            continue

        construction_key = matched_model

        if construction_key not in construction_map:
            construction_map[construction_key] = []

        append_unique(
            construction_map[construction_key],
            construction,
        )

    return construction_map


def merge_constructions(
    base_constructions: list[str],
    extra_constructions: list[str],
) -> list[str]:
    merged = []

    for value in base_constructions or []:
        append_unique(merged, value)

    for value in extra_constructions or []:
        append_unique(merged, value)

    return merged


def scrape_product(
    item: dict[str, Any],
    construction_map: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    url = item["product_url"]

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    json_ld_items = extract_json_ld(soup)

    page_text = clean_text(
        soup.get_text(" ", strip=True)
    )

    title = extract_title(
        soup,
        item.get("model_name")
        or item.get("slug"),
    )

    dimensions = extract_dimensions_from_tables(
        soup
    )

    constructions = extract_constructions(
        page_text
    )

    extra_constructions = []

    if construction_map:
        extra_constructions = construction_map.get(
            item.get("slug"),
            [],
        )

    constructions = merge_constructions(
        constructions,
        extra_constructions,
    )

    fin_setups = extract_fin_setups(
        page_text
    )

    images = extract_images(
        soup,
        json_ld_items,
    )

    return {
        "brand": "Channel Islands",
        "source": "channel_islands_model_page",
        "slug": item["slug"],
        "model_name": title,
        "model_key": item["slug"],
        "product_url": url,
        "region": item.get("region"),
        "description": extract_description(
            soup,
            json_ld_items,
        ),
        "constructions": constructions,
        "fin_setups": fin_setups,
        "sizes": dimensions,
        "official_image_url": (
            images[0]
            if images
            else None
        ),
        "images": images,
    }


def main() -> None:
    if not INPUT_LINKS.exists():
        raise FileNotFoundError(
            f"Missing input file: {INPUT_LINKS}"
        )

    links = json.loads(
        INPUT_LINKS.read_text(
            encoding="utf-8"
        )
    )

    links = [
        item
        for item in links
        if item["slug"] not in INVALID_MODEL_SLUGS
    ]

    catalogue = []
    failures = []

    print(
        f"Loading {len(links)} CI model links"
    )

    print("Loading CI AU stock construction evidence")
    construction_map = build_stock_construction_map(links)
    print(
        f"Stock construction evidence models: "
        f"{len(construction_map)}"
    )

    for index, item in enumerate(
        links,
        start=1,
    ):
        print(
            f"[{index}/{len(links)}] "
            f"{item['slug']}"
        )

        try:
            record = scrape_product(
                item,
                construction_map,
            )

            catalogue.append(record)

            print(
                f"  sizes={len(record['sizes'])} "
                f"constructions={record['constructions']} "
                f"fins={record['fin_setups']}"
            )

        except Exception as exc:
            failures.append(
                {
                    "slug": item.get("slug"),
                    "product_url": item.get(
                        "product_url"
                    ),
                    "error": str(exc),
                }
            )

            print(f"  FAILED: {exc}")

    OUTPUT_FILE.write_text(
        json.dumps(
            catalogue,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = {
        "models_input": len(links),
        "models_scraped": len(catalogue),
        "failures": len(failures),
        "models_with_sizes": sum(
            1
            for item in catalogue
            if item["sizes"]
        ),
        "models_with_images": sum(
            1
            for item in catalogue
            if item["official_image_url"]
        ),
        "total_sizes": sum(
            len(item["sizes"])
            for item in catalogue
        ),
        "failure_details": failures,
    }

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print(
        "CI master catalogue build complete"
    )
    print(
        f"Models scraped: "
        f"{report['models_scraped']}"
    )
    print(
        f"Models with sizes: "
        f"{report['models_with_sizes']}"
    )
    print(
        f"Models with images: "
        f"{report['models_with_images']}"
    )
    print(
        f"Total sizes: "
        f"{report['total_sizes']}"
    )
    print(
        f"Failures: "
        f"{report['failures']}"
    )

    print(OUTPUT_FILE)
    print(REPORT_FILE)


if __name__ == "__main__":
    main()
