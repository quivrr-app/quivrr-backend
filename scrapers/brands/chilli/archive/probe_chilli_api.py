import json
from pathlib import Path

import requests


API_URL = "https://chilli.shaperbuddy.com/api/v1/shop/surfboards?top=3"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


response = requests.get(
    API_URL,
    headers=HEADERS,
    timeout=(10, 30),
)

print("")
print("=" * 100)
print("STATUS")
print("=" * 100)
print(response.status_code)

print("")
print("=" * 100)
print("CONTENT TYPE")
print("=" * 100)
print(response.headers.get("content-type"))

print("")
print("=" * 100)
print("FIRST 2000 CHARS")
print("=" * 100)
print(response.text[:2000])

output = Path("scrapers/brands/chilli/output/chilli_api_probe.json")

output.write_text(
    response.text,
    encoding="utf-8",
)

print("")
print("Saved:", output)
