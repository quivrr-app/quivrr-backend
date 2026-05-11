import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


DEFAULT_PRODUCT_URL = "https://jsindustries.com/products/xero-gravity"

OUTPUT_DIR = Path("logs")
OUTPUT_DIR.mkdir(exist_ok=True)


def safe_name_from_url(url):
    path = urlparse(url).path.strip("/")
    name = path.split("/")[-1] or "js_product"

    name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        name
    )

    return name


def main() -> None:

    product_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else DEFAULT_PRODUCT_URL
    )

    output_name = safe_name_from_url(product_url)

    html_path = OUTPUT_DIR / f"{output_name}_rendered.html"
    text_path = OUTPUT_DIR / f"{output_name}_rendered.txt"

    print(f"Debugging: {product_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        page = browser.new_page(
            viewport={
                "width": 1600,
                "height": 1400
            }
        )

        page.goto(
            product_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(6000)

        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(2000)

        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(2000)

        html = page.content()
        text = page.locator("body").inner_text()

        html_path.write_text(
            html,
            encoding="utf-8"
        )

        text_path.write_text(
            text,
            encoding="utf-8"
        )

        print("Saved rendered JS product files:")
        print(f"- {html_path}")
        print(f"- {text_path}")

        browser.close()


if __name__ == "__main__":
    main()