import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BRAND_NAME = "Misfit Shapes"
BASE_URL = "https://misfitshapes.com"
COLLECTION_URL = "https://misfitshapes.com/collections/current-models"
OUTPUT_FILE = Path("scrapers/brands/misfit/output/misfit_master_catalogue_clean.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SIZE_ROW_RE = re.compile(
    r"(?P<length>[4-9]'\d{1,2})\s+"
    r"(?P<width>\d{1,2}(?:\s+\d/\d|\.\d+)?)\s+"
    r"(?P<thickness>\d(?:\s+\d/\d+|\.\d+)?)\s+"
    r"(?P<volume>\d{2}(?:\.\d+)?)\s+"
    r"(?P<rest>.*?)(?:Custom Order|Add to Cart|$)",
    re.IGNORECASE,
)

TAIL_TERMS = [
    "ROUND PIN",
    "ROUND",
    "DIAMOND",
    "SWALLOW",
    "SQUASH",
    "PIN",
    "FISH",
]

FIN_RE = re.compile(
    r"(?P<fin>(?:\d\s*FIN\s*)?(?:FCS\s*2|FCS\s*II|FUTURES)(?:\s*/\s*(?:FCS\s*2|FCS\s*II|FUTURES))?)",
    re.IGNORECASE,
)


def clean(value):
    value = str(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def get_html(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def html_to_text(html):
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return soup.get_text(" ", strip=True)


def discover_product_urls():
    html = get_html(COLLECTION_URL)
    soup = BeautifulSoup(html, "html.parser")

    urls = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]

        if "/collections/current-models/products/" not in href:
            continue

        url = urljoin(BASE_URL, href.split("?")[0])

        if url not in urls:
            urls.append(url)

    return urls


def extract_title(soup, fallback_url):
    meta = soup.find("meta", property="og:title")

    if meta and meta.get("content"):
        title = clean(meta["content"])

        if title:
            title = title.replace("| Misfit Shapes", "").strip()
            title = title.replace("? Misfit Shapes", "").strip()
            title = title.replace("- Misfit Shapes", "").strip()

            if title and title.lower() != "your cart":
                return title

    product_json = soup.find("script", type="application/ld+json")

    if product_json:
        try:
            import json
            data = json.loads(product_json.string or "{}")

            if isinstance(data, dict):
                name = clean(data.get("name"))

                if name and name.lower() != "your cart":
                    return name
        except Exception:
            pass

    slug = fallback_url.rstrip("/").split("/")[-1]
    return clean(slug.replace("-", " ").title())


def extract_image(soup):
    og = soup.find("meta", property="og:image")

    if og and og.get("content"):
        return clean(og["content"])

    image = soup.find("img")

    if image and image.get("src"):
        return urljoin(BASE_URL, image["src"])

    return None


def normalise_fin(value):
    value = clean(value)

    if not value:
        return None

    value = value.upper()
    value = value.replace("FCS 2", "FCS II")
    value = value.replace("FCS2", "FCS II")
    value = value.replace(" / ", "/")
    value = value.replace("/", " / ")
    value = re.sub(r"\s+", " ", value).strip()

    return value


def extract_tail(rest):
    text = clean(rest) or ""
    upper = text.upper()

    for term in TAIL_TERMS:
        if term in upper:
            return term.title()

    return None


def extract_fin(rest):
    match = FIN_RE.search(rest or "")

    if not match:
        return None

    return normalise_fin(match.group("fin"))


def parse_sizes_from_dom(soup):
    rows = []
    seen = set()

    for table in soup.find_all("table"):
        headers = [
            clean(cell.get_text(" ", strip=True))
            for cell in table.find_all("th")
        ]
        header_text = " ".join([h or "" for h in headers]).lower()

        if "height" not in header_text or "volume" not in header_text:
            continue

        for tr in table.find_all("tr"):
            cells = [
                clean(cell.get_text(" ", strip=True))
                for cell in tr.find_all(["td", "th"])
            ]
            cells = [cell for cell in cells if cell is not None]

            if len(cells) < 7:
                continue

            length = clean(cells[0])
            width = clean(cells[1])
            thickness = clean(cells[2])
            volume_text = clean(cells[3])
            tail = clean(cells[5])
            fin = clean(cells[6])

            if not length or not re.match(r"^[4-9]'\d{1,2}$", length):
                continue

            try:
                volume = float(str(volume_text).replace("L", "").strip())
            except ValueError:
                continue

            row = {
                "length": length,
                "width": width,
                "thickness": thickness,
                "volume_litres": volume,
                "tail_shape": tail,
                "fin_system": normalise_fin(fin),
            }

            key = (
                row["length"],
                row["width"],
                row["thickness"],
                row["volume_litres"],
                row.get("tail_shape"),
                row.get("fin_system"),
            )

            if key in seen:
                continue

            seen.add(key)
            rows.append(row)

    return rows


def parse_sizes(text):
    rows = []
    seen = set()

    stock_index = text.lower().find("stock dimensions")

    if stock_index >= 0:
        text = text[stock_index:]

    for match in SIZE_ROW_RE.finditer(text):
        rest = clean(match.group("rest")) or ""

        try:
            volume = float(match.group("volume"))
        except ValueError:
            continue

        row = {
            "length": clean(match.group("length")),
            "width": clean(match.group("width")),
            "thickness": clean(match.group("thickness")),
            "volume_litres": volume,
            "tail_shape": extract_tail(rest),
            "fin_system": extract_fin(rest),
        }

        key = (
            row["length"],
            row["width"],
            row["thickness"],
            row["volume_litres"],
            row.get("tail_shape"),
            row.get("fin_system"),
        )

        if key in seen:
            continue

        seen.add(key)
        rows.append(row)

    return rows


def build_catalogue():
    print("")
    print("Building Misfit Shapes manufacturer catalogue")
    print(f"Source: {COLLECTION_URL}")
    print("")

    product_urls = discover_product_urls()

    if not product_urls:
        raise RuntimeError("No Misfit product URLs discovered")

    print(f"Product URLs discovered: {len(product_urls)}")

    rows = []
    seen = set()

    for product_url in product_urls:
        html = get_html(product_url)
        soup = BeautifulSoup(html, "html.parser")
        text = html_to_text(html)

        model = extract_title(soup, product_url)
        image_url = extract_image(soup)
        sizes = parse_sizes_from_dom(soup)

        if not sizes:
            sizes = parse_sizes(text)

        print(f"{model}: {len(sizes)} stock sizes")

        for size in sizes:
            key = (
                model,
                size["length"],
                size["width"],
                size["thickness"],
                size["volume_litres"],
                size.get("tail_shape"),
                size.get("fin_system"),
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
                "fin_system": size.get("fin_system"),
                "tail_shape": size.get("tail_shape"),
                "official_product_url": product_url,
                "official_image_url": image_url,
                "source": COLLECTION_URL,
                "source_product_title": model,
                "source_product_id": None,
                "source_variant_id": None,
                "source_variant_title": None,
                "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
            })

        time.sleep(0.4)

    if not rows:
        raise RuntimeError("No Misfit catalogue rows were built")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    report_file = OUTPUT_FILE.with_name("misfit_master_catalogue_clean_report.json")
    report_file.write_text(
        json.dumps(
            {
                "brand": BRAND_NAME,
                "collection_url": COLLECTION_URL,
                "products_seen": len(product_urls),
                "catalogue_rows": len(rows),
                "models": sorted(set(row["model"] for row in rows)),
                "output_file": str(OUTPUT_FILE),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print("Misfit catalogue build complete")
    print(f"Rows: {len(rows)}")
    print(f"Models: {len(set(row['model'] for row in rows))}")
    print(f"Output: {OUTPUT_FILE}")
    print("")


if __name__ == "__main__":
    try:
        build_catalogue()
    except Exception as exc:
        print("")
        print(f"Misfit catalogue build failed: {exc}")
        print("")
        sys.exit(1)
