from pathlib import Path


path = Path("scrapers/brands/christenson/probe_christenson_dimensions.py")

path.write_text(r'''
import json
import re
from pathlib import Path

import requests


INPUT_FILE = Path(
    "scrapers/brands/christenson/output/christenson_model_links.json"
)

OUTPUT_FILE = Path(
    "scrapers/brands/christenson/output/christenson_dimension_probe.json"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


links = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

results = []


dimension_pattern = re.compile(
    r"""
    \d+'\d{1,2}
    \s*x\s*
    \d+(?:\s+\d+/\d+|\.\d+)?
    \s*x\s*
    \d+(?:\s+\d+/\d+|\.\d+)?
    """,
    re.IGNORECASE | re.VERBOSE,
)

volume_pattern = re.compile(
    r"(\d+(?:\.\d+)?)\s*L",
    re.IGNORECASE,
)


print("")
print("=" * 100)
print("CHRISTENSON DIMENSION PROBE")
print("=" * 100)

for row in links:

    url = row["url"]

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=(10, 30),
        )

        response.raise_for_status()

        html = response.text

        html = (
            html
            .replace("’", "'")
            .replace("”", '"')
            .replace("“", '"')
            .replace("&quot;", '"')
            .replace("&nbsp;", " ")
        )

        dimensions = []
        seen = set()

        for match in dimension_pattern.finditer(html):

            dimension = " ".join(match.group(0).split())

            if dimension not in seen:
                seen.add(dimension)
                dimensions.append(dimension)

        volumes = volume_pattern.findall(html)

        results.append({
            "name": row["name"],
            "url": url,
            "dimension_count": len(dimensions),
            "dimensions": dimensions[:80],
            "volumes_found": volumes[:80],
        })

        print("")
        print("-" * 100)
        print(row["name"])
        print("Dimensions:", len(dimensions))

        for item in dimensions[:15]:
            print(" -", item)

    except Exception as exc:

        print("")
        print("FAILED:", url)
        print(exc)

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("=" * 100)
print("SUMMARY")
print("=" * 100)
print("Models inspected:", len(results))
print("Saved:", OUTPUT_FILE)
'''.strip() + "\n", encoding="utf-8")

print("Updated Christenson dimension parser")
