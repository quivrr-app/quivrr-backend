import json
from pathlib import Path

import requests


BASE_URL = "https://rustysurfboards.com"
OUTPUT_FILE = Path("scrapers/brands/rusty/output/rusty_all_collections.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}


def main():
    url = f"{BASE_URL}/collections.json?limit=250"
    response = requests.get(url, headers=HEADERS, timeout=(10, 30))
    response.raise_for_status()

    data = response.json()
    collections = data.get("collections", [])

    rows = []

    print("")
    print("=" * 80)
    print("RUSTY COLLECTION DISCOVERY")
    print("=" * 80)

    for collection in collections:
        handle = collection.get("handle")
        title = collection.get("title")

        text = f"{handle} {title}".lower()

        likely_board_collection = any(word in text for word in [
            "surfboard",
            "shortboard",
            "alternative",
            "fish",
            "step",
            "mid",
            "longboard",
            "grom",
            "performance",
            "twin",
            "gun",
            "high performance",
            "big board",
        ])

        row = {
            "handle": handle,
            "title": title,
            "likely_board_collection": likely_board_collection,
            "url": f"{BASE_URL}/collections/{handle}",
        }

        rows.append(row)

        if likely_board_collection:
            print(f"{handle} | {title}")

    OUTPUT_FILE.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("Collections found:", len(rows))
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
