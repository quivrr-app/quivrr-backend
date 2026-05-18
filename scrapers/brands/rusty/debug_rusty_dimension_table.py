from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://rustysurfboards.eu/products/rusty-heckler-hybrid-fish-surfboard#dimensions"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    try:
        page.get_by_role("button", name="Accept").click(timeout=3000)
        page.wait_for_timeout(1000)
    except Exception:
        pass

    try:
        page.locator("#dimensions").scroll_into_view_if_needed(timeout=5000)
        page.wait_for_timeout(2000)
    except Exception:
        pass

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    tables = soup.find_all("table")

    print("")
    print("Tables:", len(tables))

    for i, table in enumerate(tables, start=1):
        print("")
        print("=" * 80)
        print("TABLE", i)
        print("=" * 80)

        for row in table.find_all("tr"):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"])
            ]

            if cells:
                print(" | ".join(cells))

    print("")
    print("=" * 80)
    print("TEXT CANDIDATES")
    print("=" * 80)

    text = soup.get_text("\n", strip=True)

    for line in text.splitlines():
        line = line.strip()

        if (
            "Length" in line
            or "Width" in line
            or "Thickness" in line
            or "Volume" in line
            or "5'4" in line
            or "5'6" in line
            or "6'0" in line
        ):
            print(line)

    browser.close()
