import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


OUTPUT_FILE = Path("scrapers/brands/lost/output/lost_construction_collections.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

COLLECTIONS = {
    "LightSpeed": "https://lostsurfboards.com.au/collections/lightspeed",
    "Black Sheep": "https://lostsurfboards.com.au/collections/black-sheep",
    "Lib Tech": "https://lostsurfboards.com.au/collections/lib-tech",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalise_model_name(value):
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

    return value


def extract_collection_models(construction, url):
    response = requests.get(url, headers=HEADERS, timeout=(10, 30))
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    rows = []
    seen = set()

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

        model = normalise_model_name(text)

        if not model or len(model) < 3:
            continue

        if model.lower() in ["view", "view all", "quick view", "add to cart", "sale", "sold out"]:
            continue

        key = (construction, model, full_url)

        if key in seen:
            continue

        seen.add(key)

        rows.append({
            "construction": construction,
            "model": model,
            "source_text": text,
            "source_url": full_url,
            "collection_url": url,
        })

    return rows


def main():
    all_rows = []

    print("")
    print("=" * 80)
    print("LOST CONSTRUCTION COLLECTION DISCOVERY")
    print("=" * 80)

    for construction, url in COLLECTIONS.items():
        rows = extract_collection_models(construction, url)
        all_rows.extend(rows)

        print("")
        print(construction)
        print("Rows:", len(rows))
        for row in rows[:40]:
            print(" -", row["model"], "|", row["source_text"])

    OUTPUT_FILE.write_text(
        json.dumps(all_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("Saved:", OUTPUT_FILE)
    print("Total rows:", len(all_rows))


if __name__ == "__main__":
    main()
