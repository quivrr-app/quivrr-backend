import re
import requests
from pathlib import Path

url = "https://sharpeyesurfboards.com/products/inferno-73"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}

response = requests.get(url, headers=headers, timeout=(10, 30))

html = response.text

out = Path("scrapers/brands/sharpeye/output/sharpeye_raw_dimension_context.txt")

contexts = []

patterns = [
    "5'10",
    "5’10",
    "28.6",
    "Stock Dimensions",
]

for pattern in patterns:

    for match in re.finditer(re.escape(pattern), html, flags=re.IGNORECASE):

        start = max(0, match.start() - 500)
        end = min(len(html), match.end() + 500)

        contexts.append(
            "\n" + "=" * 100 + "\n" +
            f"PATTERN: {pattern}\n" +
            "=" * 100 + "\n" +
            html[start:end]
        )

out.write_text(
    "\n".join(contexts),
    encoding="utf-8",
)

print(out)
print("Contexts found:", len(contexts))
