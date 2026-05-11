from pathlib import Path

from playwright.sync_api import sync_playwright


PRODUCT_URL = "https://jsindustries.com/products/xero-gravity"
OUTPUT_DIR = Path("logs")
OUTPUT_DIR.mkdir(exist_ok=True)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1600, "height": 1400})

        page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)

        page.wait_for_timeout(8000)

        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(3000)

        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(4000)

        html = page.content()
        text = page.locator("body").inner_text()

        (OUTPUT_DIR / "js_xero_gravity_rendered.html").write_text(html, encoding="utf-8")
        (OUTPUT_DIR / "js_xero_gravity_rendered.txt").write_text(text, encoding="utf-8")

        print("Saved rendered JS product HTML and text to logs folder.")
        print("Open logs\\js_xero_gravity_rendered.txt and search for Xero Gravity, HEIGHT, WIDTH, THICKNESS or VOLUME.")

        browser.close()


if __name__ == "__main__":
    main()