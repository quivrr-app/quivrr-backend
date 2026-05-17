import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("scrapers/brands/channel_islands/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "ci_canonical_model_links.json"

TARGETS = [
    {
        "region": "au",
        "source": "board-models",
        "url": "https://shop-au.cisurfboards.com/collections/board-models",
    },
    {
        "region": "global",
        "source": "board-models",
        "url": "https://cisurfboards.com/collections/board-models",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)"
}

INVALID_SLUG_PARTS = [
    "#",
    "gift-card",
    "e-gift",
    "accessories",
    "wetsuit",
]


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    return " ".join(value.split()).strip()


def fetch_models(target: dict) -> list:
    print(f"Scraping {target['url']}")

    response = requests.get(
        target["url"],
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/products/" not in href:
            continue

        href = href.split("?")[0].split("#")[0]

        slug = href.rstrip("/").split("/")[-1].lower()

        if not slug:
            continue

        if any(part in slug for part in INVALID_SLUG_PARTS):
            continue

        title = clean_text(link.get_text(" ", strip=True))

        if not title:
            continue

        if href.startswith("/"):
            base = "https://shop-au.cisurfboards.com"

            if target["region"] == "global":
                base = "https://cisurfboards.com"

            href = base + href

        results[slug] = {
            "slug": slug,
            "model_name": title,
            "product_url": href,
            "region": target["region"],
            "source": target["source"],
        }

    return list(results.values())


def main() -> None:
    merged = {}

    for target in TARGETS:
        try:
            items = fetch_models(target)

            for item in items:
                slug = item["slug"]

                if slug not in merged:
                    merged[slug] = item
                    continue

                existing = merged[slug]

                if existing["region"] == "au" and item["region"] == "global":
                    merged[slug] = item

        except Exception as exc:
            print(f"FAILED {target['url']}: {exc}")

    final = sorted(
        merged.values(),
        key=lambda x: x["model_name"].lower()
    )

    OUTPUT_FILE.write_text(
        json.dumps(final, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print(f"Saved {len(final)} canonical CI models")
    print(OUTPUT_FILE)

    print("")
    print("Models:")
    for item in final:
        print(f"{item['model_name']} | {item['slug']} | {item['region']}")


if __name__ == "__main__":
    main()
