from pathlib import Path

path = Path("scrapers/brands/sharpeye/test_sharpeye_playwright.py")

path.write_text(r'''
from playwright.sync_api import sync_playwright


URL = "https://sharpeyesurfboards.com/products/inferno-73"


with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
    )

    page = browser.new_page()

    page.goto(
        URL,
        wait_until="networkidle",
        timeout=120000,
    )

    page.wait_for_timeout(5000)

    print("")
    print("=" * 100)
    print("PAGE TITLE")
    print("=" * 100)
    print(page.title())

    print("")
    print("=" * 100)
    print("MATCHING TEXT")
    print("=" * 100)

    body_text = page.locator("body").inner_text()

    lines = body_text.splitlines()

    for line in lines:

        line = line.strip()

        if "'" in line and "L" in line:
            print(line)

    print("")
    print("=" * 100)
    print("HTML LENGTH")
    print("=" * 100)

    html = page.content()

    print(len(html))

    browser.close()
'''.strip() + "\n", encoding="utf-8")

print("Created Sharp Eye Playwright tester")
