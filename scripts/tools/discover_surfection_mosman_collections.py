import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://surfectionmosman.com"

checks = [
    "/collections/all",
    "/collections/surfboards",
    "/collections/surfboard",
    "/collections/boards",
    "/collections/hardboards",
    "/collections/shortboards",
    "/collections/longboards",
    "/sitemap_collections_1.xml",
    "/sitemap.xml",
]

headers = {"User-Agent": "Mozilla/5.0"}

print()
print("Surfection Mosman collection discovery")
print("--------------------------------------")

for path in checks:
    url = urljoin(BASE_URL, path)
    try:
        r = requests.get(url, headers=headers, timeout=20)
        print(f"{path}: {r.status_code} {r.url}")

        text = r.text[:20000]

        handles = sorted(set(re.findall(r"/collections/([a-zA-Z0-9\-_]+)", text)))

        if handles:
            print("  Handles:")
            for handle in handles[:40]:
                print("   -", handle)

    except Exception as exc:
        print(f"{path}: ERROR {exc}")
