from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://rustysurfboards.eu/products/rusty-1984-hybrid-surfboard"


with sync_playwright() as p:

    browser = p.chromium.launch(headless=False)

    page = browser.new_page()

    page.goto(URL, wait_until="networkidle")

    page.wait_for_timeout(5000)

    html = page.content()

    print("")
    print("=" * 80)
    print("PAGE TITLE")
    print("=" * 80)
    print(page.title())

    print("")
    print("=" * 80)
    print("DIMENSION TEXT")
    print("=" * 80)

    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text("\n", strip=True)

    for line in text.splitlines():

        line = line.strip()

        if "L" in line and "x" in line:
            print(line)

    browser.close()
