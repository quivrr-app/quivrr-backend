from pathlib import Path

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")
lines = path.read_text(encoding="utf-8").splitlines()

start = None
end = None

for index, line in enumerate(lines):
    if line.startswith("def extract_dimensions_from_html"):
        start = index
    elif start is not None and line.startswith("def fetch_products"):
        end = index
        break

if start is None or end is None:
    raise RuntimeError("Could not locate extract_dimensions_from_html block")

new_block = [
    "def extract_dimensions_from_html(product_url):",
    "    response = requests.get(",
    "        product_url,",
    "        headers=HEADERS,",
    "        timeout=(10, 30),",
    "    )",
    "",
    "    soup = BeautifulSoup(response.text, 'html.parser')",
    "",
    "    matches = []",
    "",
    "    for element in soup.select('.surfboard_product_item--title'):",
    "        value = clean(element.get_text(' ', strip=True))",
    "",
    "        if re.search(r\"\\d+'\\s*\\d{1,2}\\\"?\\s*x\\s*\\d\", value, flags=re.IGNORECASE):",
    "            matches.append(value)",
    "",
    "    cleaned = []",
    "",
    "    for match in matches:",
    "        value = clean(match)",
    "        value = value.replace('×', 'x')",
    "",
    "        if value not in cleaned:",
    "            cleaned.append(value)",
    "",
    "    return cleaned",
    "",
]

updated = lines[:start] + new_block + lines[end:]

path.write_text(
    '\\n'.join(updated) + '\\n',
    encoding='utf-8',
)

print('Patched Sharp Eye dimension extraction using product title elements')
