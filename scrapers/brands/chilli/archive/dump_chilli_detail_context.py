import re
from pathlib import Path

import requests


BASE_URL = "https://www.chillisurfboards.com"
URL = "https://www.chillisurfboards.com/surfboards/detail.php?id=25279&direct=1&region=aus"

OUTPUT_FILE = Path("scrapers/brands/chilli/output/chilli_raw_detail_context.txt")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})

session.get(
    f"{BASE_URL}/changeregion.php?region=aus",
    timeout=(10, 30),
)

response = session.get(
    URL,
    timeout=(10, 30),
)

html = response.text

patterns = [
    "volume",
    "litre",
    "length",
    "width",
    "thickness",
    "stock",
    "dimensions",
    "surfboard",
    "model",
]

contexts = []

for pattern in patterns:

    for match in re.finditer(pattern, html, flags=re.IGNORECASE):

        start = max(0, match.start() - 700)
        end = min(len(html), match.end() + 700)

        contexts.append(
            "\n" + "=" * 100 + "\n" +
            f"PATTERN: {pattern}\n" +
            "=" * 100 + "\n" +
            html[start:end]
        )

print("Status:", response.status_code)
print("Final URL:", response.url)
print("HTML length:", len(html))
print("Contexts:", len(contexts))

OUTPUT_FILE.write_text(
    "\n".join(contexts[:80]),
    encoding="utf-8",
)

print("Saved:", OUTPUT_FILE)
