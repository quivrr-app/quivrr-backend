import requests
from bs4 import BeautifulSoup

url = "https://cisurfboards.com/products/ci-pro"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers, timeout=30)

print(f"Status: {response.status_code}")

html = response.text

print("")
print("DIMENSION TOKENS")
print("================")

tokens = [
    "volume",
    "litres",
    "dims",
    "dimensions",
    "size",
    "stockSizes",
    "board_size",
]

for token in tokens:
    if token.lower() in html.lower():
        print(f"FOUND: {token}")

print("")
print("TABLES")
print("======")

soup = BeautifulSoup(html, "html.parser")

tables = soup.find_all("table")

print(f"Tables found: {len(tables)}")

for index, table in enumerate(tables[:5], start=1):
    print("")
    print(f"TABLE {index}")
    print(table.get_text(" ", strip=True)[:3000])

print("")
print("SCRIPT SNIPPETS")
print("================")

scripts = soup.find_all("script")

matches = 0

for script in scripts:
    text = script.get_text(" ", strip=True)

    if any(token.lower() in text.lower() for token in tokens):
        matches += 1

        print("")
        print(f"SCRIPT MATCH {matches}")
        print(text[:4000])

        if matches >= 5:
            break
