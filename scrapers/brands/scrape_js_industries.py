import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from scrapers.brands.normalise_js_models import normalise_js_models


JS_MODELS_URL = "https://jsindustries.com/collections/surfboards"
BASE_URL = "https://jsindustries.com"


def fetch_page(url: str) -> str:
    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0 Safari/537.36"
            )
        },
        timeout=30
    )
    response.raise_for_status()
    return response.text


def extract_board_models(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    boards = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = link.get_text(" ", strip=True)

        if not href.startswith("/products/"):
            continue

        if not title:
            continue

        key = (title.lower(), href.lower())

        if key in seen:
            continue

        seen.add(key)

        boards.append({
            "model_name": title,
            "url": f"{BASE_URL}{href}"
        })

    return boards


def main() -> None:
    print("Fetching JS Industries models...")

    html = fetch_page(JS_MODELS_URL)
    raw_models = extract_board_models(html)
    normalised_models = normalise_js_models(raw_models)

    print(f"Found {len(raw_models)} raw model listings")
    print(f"Normalised to {len(normalised_models)} catalogue records")

    for model in normalised_models:
        flags = []

        if model["is_softboard"]:
            flags.append("softboard")

        if model["is_youth"]:
            flags.append("youth")

        if model["is_easy_rider"]:
            flags.append("easy rider")

        flag_text = f" [{', '.join(flags)}]" if flags else ""

        print(f"- {model['model_name']}{flag_text}")
        print(f"  Raw: {model['raw_model_name']}")
        print(f"  URL: {model['official_product_url']}")


if __name__ == "__main__":
    main()