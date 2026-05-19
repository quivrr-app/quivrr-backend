from pathlib import Path

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")
text = path.read_text(encoding="utf-8")

old = '''def extract_dimensions_from_html(product_url):
    response = requests.get(
        product_url,
        headers=HEADERS,
        timeout=(10, 30),
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    candidates = []

    for element in soup.select(".surfboard_product_item--title"):
        value = clean(element.get_text(" ", strip=True))

        if re.search(r"\\d+'\\s*\\d{1,2}", value) and "L" in value.upper():
            candidates.append(value)

    if not candidates:
        visible_text = soup.get_text(" ", strip=True)
        visible_text = clean(visible_text)

        candidates = re.findall(
            r"\\d+'\\s*\\d{1,2}\\\"?\\s*x\\s*\\d+(?:\\.\\d+)?\\s*x\\s*\\d+(?:\\.\\d+)?\\s+\\d+(?:\\.\\d+)?\\s*L",
            visible_text,
            flags=re.IGNORECASE,
        )

    cleaned = []

    for candidate in candidates:
        value = clean(candidate).replace("×", "x")

        if parse_dimensions(value)["length"] and value not in cleaned:
            cleaned.append(value)

    return cleaned
'''

new = '''def extract_dimensions_from_html(product_url):
    response = requests.get(
        product_url,
        headers=HEADERS,
        timeout=(10, 30),
    )
    response.raise_for_status()

    html = response.text
    html = html.replace("\\r", " ")
    html = html.replace("\\n", " ")
    html = html.replace("×", "x")

    matches = re.findall(
        r"\\d+'\\s*\\d{1,2}\\\"?\\s*x\\s*\\d+(?:\\.\\d+)?\\s*x\\s*\\d+(?:\\.\\d+)?\\s+\\d+(?:\\.\\d+)?\\s*L",
        html,
        flags=re.IGNORECASE,
    )

    cleaned = []

    for match in matches:
        value = clean(match)
        value = value.replace("\\\\"", "")
        value = value.replace('"', "")

        if parse_dimensions(value)["length"] and value not in cleaned:
            cleaned.append(value)

    return cleaned
'''

if old not in text:
    raise RuntimeError("Could not find current extract_dimensions_from_html function")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("Replaced Sharp Eye extraction with raw HTML direct regex")
