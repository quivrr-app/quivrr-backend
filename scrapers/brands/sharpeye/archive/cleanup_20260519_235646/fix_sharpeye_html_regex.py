from pathlib import Path

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")

text = path.read_text(encoding="utf-8")

old = r'''    matches = re.findall(
        r"(\d+'\s*\d{1,2}[\"”″]?\s*[xX]\s*\d+(?:\.\d+)?\s*[xX]\s*\d+(?:\.\d+)?\s*[xX]\s*\d+(?:\.\d+)?\s*L)",
        html,
        flags=re.IGNORECASE,
    )

    return sorted(set(matches))
'''

new = r'''    html = html.replace("&quot;", '"')
    html = html.replace("\\/", "/")
    html = re.sub(r"<[^>]+>", " ", html)

    matches = re.findall(
        r"(\d+'\s*\d{1,2}\s*[xX×]\s*\d+(?:\.\d+)?\s*[xX×]\s*\d+(?:\.\d+)?\s*[xX×]\s*\d+(?:\.\d+)?\s*L)",
        html,
        flags=re.IGNORECASE,
    )

    cleaned = []

    for match in matches:

        value = clean(match)

        value = value.replace("×", "x")

        cleaned.append(value)

    return sorted(set(cleaned))
'''

if old not in text:
    raise RuntimeError("Could not find HTML fallback block")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("Updated Sharp Eye HTML dimension extraction regex")
