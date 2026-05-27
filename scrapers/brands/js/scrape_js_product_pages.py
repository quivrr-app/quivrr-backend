import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright


OUTPUT_FILE = Path("scrapers/brands/js/output/js_page_catalogue.json")

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


MODEL_BY_SLUG = {
    "mother-trucker": "Mother Trucker",
    "step-off-performer": "Step Off",
    "forget-me-not-3-step-up": "Forget Me Not 3 Step Up",
    "big-horse": "Big Horse",
    "golden-child": "Golden Child",
    "forget-me-not-3": "Forget Me Not 3",
    "monsta": "Monsta",
    "schooner": "Schooner",
    "raging-bull": "Raging Bull",
    "xero-gravity": "Xero Gravity",
    "xero-fusion": "Xero Fusion",
    "el-baron": "El Baron",
    "big-baron": "Big Baron",
    "black-baron": "Black Baron",
    "bull-run": "Bull Run",
    "sub-xero": "Sub Xero",
    "flame-fish": "Flame Fish",
    "golden-child-youth": "Golden Child Youth",
    "monsta-youth": "Monsta Youth",
    "xero-gravity-youth": "Xero Gravity Youth",
    "black-eagle-2": "Black Eagle 2",
    "big-baron-easy-rider-softboard": "Big Baron Easy Rider",
    "big-baron-softboard": "Big Baron Softboard",
    "bull-run-softboard": "Bull Run Softboard",
    "flame-fish-softboard": "Flame Fish Softboard",
    "golden-child-easy-rider": "Golden Child Easy Rider",
    "monsta-easy-rider": "Monsta Easy Rider",
    "xero-gravity-easy-rider": "Xero Gravity Easy Rider",
    "xero-fusion-easy-rider": "Xero Fusion Easy Rider",
    "raging-bull-easy-rider-1": "Raging Bull Easy Rider",
}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def model_from_url(url):
    slug = url.rstrip("/").split("/")[-1]
    return MODEL_BY_SLUG.get(
        slug,
        slug.replace("-", " ").title()
    )


def normalise_construction(value):
    value = clean(value)

    if not value:
        return None

    upper_value = value.upper()

    if upper_value == "CARBOTUNE":
        return "CarboTune"

    if upper_value.startswith("HYFI"):
        return "HYFI 3.0"

    if upper_value in ["PU", "PE", "EPS"]:
        return upper_value

    if upper_value == "SOFTBOARD":
        return "Softboard"

    return value


def normalise_fin(value):
    value = clean(value)

    if not value:
        return None

    upper_value = value.upper()

    if "FCS" in upper_value:
        return "FCS II"

    if "FUTURES" in upper_value:
        return "Futures"

    return value


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
            "volume_litres": float(volume_match.group(1)),
        })

    return results


async def get_product_variants(page):
    product = await page.evaluate(
        """
        () => {
            if (
                window.customerHub &&
                window.customerHub.activeProduct &&
                window.customerHub.activeProduct.variants
            ) {
                return window.customerHub.activeProduct;
            }

            return null;
        }
        """
    )

    if not product:
        return []

    rows = []

    for variant in product.get("variants", []):
        construction = None
        fin_system = None

        for option in variant.get("selectedOptions", []):
            name = clean(option.get("name")).lower()
            value = clean(option.get("value"))

            if name == "construction":
                construction = normalise_construction(value)

            if name == "fin system":
                fin_system = normalise_fin(value)

        if construction:
            rows.append({
                "construction": construction,
                "fin_system": fin_system,
                "price": variant.get("price"),
                "available": variant.get("availableForSale"),
                "variant_id": variant.get("id"),
                "image_url": variant.get("imageUrl"),
            })

    deduped = {}

    for row in rows:
        key = "|".join([
            row.get("construction") or "",
            row.get("fin_system") or "",
        ])

        deduped[key] = row

    return list(deduped.values())


async def scrape_product(page, url):

    print(f"Scraping {url}")

    await page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    await page.wait_for_timeout(6000)

    await page.mouse.wheel(0, 2500)

    await page.wait_for_timeout(1500)

    text = await page.locator("body").inner_text()

    model_name = model_from_url(url)

    dimensions = parse_dimensions(text)
    variants = await get_product_variants(page)

    if not variants:
        variants = [{
            "construction": None,
            "fin_system": None,
            "price": None,
            "available": None,
            "variant_id": None,
            "image_url": None,
        }]

    rows = []

    for variant in variants:
        for dimension in dimensions:
            rows.append({
                "brand": "JS Industries",
                "model": model_name,
                "construction": variant.get("construction"),
                "fin_system": variant.get("fin_system"),
                "tail_shape": None,
                "product_url": url,
                "price": variant.get("price"),
                "available": variant.get("available"),
                "variant_id": variant.get("variant_id"),
                "image_url": variant.get("image_url"),
                **dimension,
            })

    print(f"  Model: {model_name}")
    print(f"  Dimensions: {len(dimensions)}")
    print(f"  Variant options: {len(variants)}")
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
                print(f"Failed {url}: {error}")

        await browser.close()

    deduped = {}

    for row in all_rows:

        key = "|".join([
            row.get("model") or "",
            row.get("construction") or "",
            row.get("fin_system") or "",
            row.get("length") or "",
            row.get("width") or "",
            row.get("thickness") or "",
            str(row.get("volume_litres") or ""),
        ])

        deduped[key] = row

    final_rows = list(deduped.values())

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