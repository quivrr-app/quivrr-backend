import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


INPUT_FILE = Path("scrapers/brands/christenson/output/christenson_model_links.json")
OUTPUT_FILE = Path("scrapers/brands/christenson/output/christenson_dimension_probe.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

dimension_line_pattern = re.compile(
    r"\d+'\d{1,2}\s*x\s*\d+(?:\s+\d+/\d+|\.\d+)?\s*x\s*\d+(?:\s+\d+/\d+|\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?\s*L)?",
    re.IGNORECASE,
)

volume_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*L", re.IGNORECASE)


def clean(value):
    value = str(value or "")
    value = value.replace("’", "'").replace("“", '"').replace("”", '"')
    value = value.replace("&nbsp;", " ").replace("&quot;", '"')
    return re.sub(r"\s+", " ", value).strip()


def model_name_from_page(soup, fallback_url):
    for selector in ["h1", "h2"]:
        element = soup.select_one(selector)
        if element:
            name = clean(element.get_text(" ", strip=True))
            if name and name.lower() not in ["surfboards", "performance"]:
                return name

    slug = fallback_url.rstrip("/").split("/")[-1]
    replacements = {
        "op1new": "OP1",
        "op2new": "OP2",
        "op3new": "OP3",
        "op4": "OP4",
        "chawk": "C-Hawk",
    }

    return replacements.get(slug.lower(), slug.replace("-", " ").title())


links = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

results = []

print("")
print("=" * 100)
print("CHRISTENSON DIMENSION PROBE")
print("=" * 100)

for row in links:
    url = row["url"]

    try:
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        response.raise_for_status()

        html = clean(response.text)
        soup = BeautifulSoup(response.text, "html.parser")

        model_name = model_name_from_page(soup, url)

        text = soup.get_text("\n", strip=True)
        text = text.replace("’", "'").replace("“", '"').replace("”", '"')
        lines = [clean(line) for line in text.splitlines() if clean(line)]

        current_group = "PU"
        specs = []

        for line in lines:
            lower = line.lower()

            if "standard dimensions" in lower:
                current_group = "Standard"
                continue

            if "performance dimensions" in lower:
                current_group = "Performance"
                continue

            if "specifications" in lower:
                current_group = "PU"
                continue

            for match in dimension_line_pattern.finditer(line):
                spec = clean(match.group(0))
                volume_match = volume_pattern.search(spec)

                specs.append({
                    "dimension": spec,
                    "volume_litres": float(volume_match.group(1)) if volume_match else None,
                    "profile": current_group,
                })

        if not specs:
            for match in dimension_line_pattern.finditer(html):
                spec = clean(match.group(0))
                volume_match = volume_pattern.search(spec)

                specs.append({
                    "dimension": spec,
                    "volume_litres": float(volume_match.group(1)) if volume_match else None,
                    "profile": "PU",
                })

        seen = set()
        deduped_specs = []

        for spec in specs:
            key = (spec["dimension"], spec["profile"])

            if key in seen:
                continue

            seen.add(key)
            deduped_specs.append(spec)

        result = {
            "name": model_name,
            "url": url,
            "specification_count": len(deduped_specs),
            "specifications": deduped_specs,
        }

        results.append(result)

        print("")
        print("-" * 100)
        print(model_name)
        print("Specs:", len(deduped_specs))

        for spec in deduped_specs[:12]:
            print(" -", spec["profile"], "|", spec["dimension"], "|", spec["volume_litres"])

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
