import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright


MODELS_FILE = Path("scrapers/brands/js_canonical_models.json")
OUTPUT_FILE = Path("scrapers/brands/output/js_page_catalogue.json")

PRODUCT_URLS = [
    "https://jsindustries.com/products/mother-trucker",
    "https://jsindustries.com/products/step-off-performer",
    "https://jsindustries.com/products/forget-me-not-3-step-up",
    "https://jsindustries.com/products/big-horse",
    "https://jsindustries.com/products/golden-child",
    "https://jsindustries.com/products/forget-me-not-3",
    "https://jsindustries.com/products/monsta",
    "https://jsindustries.com/products/schooner",
    "https://jsindustries.com/products/raging-bull",
    "https://jsindustries.com/products/xero-gravity",
    "https://jsindustries.com/products/xero-fusion",
    "https://jsindustries.com/products/el-baron",
    "https://jsindustries.com/products/big-baron",
    "https://jsindustries.com/products/black-baron",
    "https://jsindustries.com/products/bull-run",
    "https://jsindustries.com/products/sub-xero",
    "https://jsindustries.com/products/flame-fish",
    "https://jsindustries.com/products/golden-child-youth",
    "https://jsindustries.com/products/monsta-youth",
    "https://jsindustries.com/products/xero-gravity-youth",
    "https://jsindustries.com/products/black-eagle-2",
    "https://jsindustries.com/products/big-baron-easy-rider-softboard",
    "https://jsindustries.com/products/big-baron-softboard",
    "https://jsindustries.com/products/bull-run-softboard",
    "https://jsindustries.com/products/flame-fish-softboard",
    "https://jsindustries.com/products/golden-child-easy-rider",
    "https://jsindustries.com/products/monsta-easy-rider",
    "https://jsindustries.com/products/xero-gravity-easy-rider",
    "https://jsindustries.com/products/xero-fusion-easy-rider",
    "https://jsindustries.com/products/raging-bull-easy-rider-1",
]


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_dimensions(text):
    lines = [
        clean(line)
        for line in text.splitlines()
        if clean(line)
    ]

    results = []

    for index, line in enumerate(lines):

        if not re.fullmatch(
            r"\d{1,2}'\d{1,2}\"",
            line
        ):
            continue

        if index + 3 >= len(lines):
            continue

        length = line
        width = lines[index + 1]
        thickness = lines[index + 2]
        volume = lines[index + 3]

        volume_match = re.fullmatch(
            r"(\d{1,3}(?:\.\d+)?)L",
            volume,
            re.IGNORECASE
        )

        if not volume_match:
            continue

        results.append({
            "length": length.replace('"', ""),
            "width": width.replace('"', ""),
            "thickness": thickness.replace('"', ""),
            "volume_litres": float(
                volume_match.group(1)
            ),
        })

    return results


def parse_options(text):

    constructions = []
    fin_systems = []
    tail_shapes = []

    upper_text = text.upper()

    if "PU" in upper_text:
        constructions.append("PU")

    if "HYFI" in upper_text:
        constructions.append("HYFI 3.0")

    if "CARBOTUNE" in upper_text:
        constructions.append("CarboTune")

    if "PE" in upper_text:
        constructions.append("PE")

    if "SOFTBOARD" in upper_text:
        constructions.append("Softboard")

    if "FCS" in upper_text:
        fin_systems.append("FCS II")

    if "FUTURES" in upper_text:
        fin_systems.append("Futures")

    if "SQUASH TAIL" in upper_text:
        tail_shapes.append("Squash Tail")

    if "ROUND TAIL" in upper_text:
        tail_shapes.append("Round Tail")

    if "SWALLOW TAIL" in upper_text:
        tail_shapes.append("Swallow Tail")

    if "PIN TAIL" in upper_text:
        tail_shapes.append("Pin Tail")

    return {
        "constructions": list(set(constructions)),
        "fin_systems": list(set(fin_systems)),
        "tail_shapes": list(set(tail_shapes)),
    }


def model_from_url(url):

    slug = url.rstrip("/").split("/")[-1]

    model = slug.replace("-", " ").title()

    model = model.replace(" Performer", "")
    model = model.replace(" Softboard", "")
    model = model.replace(" Easy Rider", "")
    model = model.replace(" 1", "")

    return clean(model)


async def scrape_product(page, url):

    print(f"Scraping {url}")

    await page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    await page.wait_for_timeout(5000)

    await page.mouse.wheel(0, 2500)

    await page.wait_for_timeout(1500)

    text = await page.locator(
        "body"
    ).inner_text()

    model_name = model_from_url(url)

    dimensions = parse_dimensions(text)

    options = parse_options(text)

    rows = []

    constructions = (
        options["constructions"]
        or [None]
    )

    fin_systems = (
        options["fin_systems"]
        or [None]
    )

    tail_shapes = (
        options["tail_shapes"]
        or [None]
    )

    for construction in constructions:
        for fin_system in fin_systems:
            for tail_shape in tail_shapes:
                for dimension in dimensions:

                    rows.append({
                        "brand": "JS Industries",
                        "model": model_name,
                        "construction": construction,
                        "fin_system": fin_system,
                        "tail_shape": tail_shape,
                        "product_url": url,
                        **dimension,
                    })

    print(f"  Model: {model_name}")
    print(f"  Dimensions: {len(dimensions)}")
    print(f"  Rows: {len(rows)}")

    return rows


async def main():

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    all_rows = []

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            viewport={
                "width": 1600,
                "height": 1400
            }
        )

        for url in PRODUCT_URLS:

            try:

                rows = await scrape_product(
                    page,
                    url
                )

                all_rows.extend(rows)

            except Exception as error:

                print(
                    f"Failed {url}: {error}"
                )

        await browser.close()

    deduped = {}

    for row in all_rows:

        key = "|".join([
            row.get("model") or "",
            row.get("construction") or "",
            row.get("fin_system") or "",
            row.get("tail_shape") or "",
            row.get("length") or "",
            row.get("width") or "",
            row.get("thickness") or "",
            str(row.get("volume_litres") or ""),
        ])

        deduped[key] = row

    final_rows = list(
        deduped.values()
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            final_rows,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("\nJS page catalogue built")
    print(f"Rows scraped: {len(all_rows)}")
    print(f"Rows deduped: {len(final_rows)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())