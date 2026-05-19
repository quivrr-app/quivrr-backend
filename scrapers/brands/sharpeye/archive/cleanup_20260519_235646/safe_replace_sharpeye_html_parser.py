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
    "    visible_text = soup.get_text(' ', strip=True)",
    "",
    "    visible_text = visible_text.replace('×', 'x')",
    '    visible_text = visible_text.replace(\'"\', "")',
    "",
    "    matches = re.findall(",
    r'        r"(\d+\'\s*\d{1,2}\s*x\s*\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s*L)",',
    "        visible_text,",
    "        flags=re.IGNORECASE,",
    "    )",
    "",
    "    cleaned = []",
    "",
    "    for match in matches:",
    "        value = clean(match)",
    "",
    "        if value not in cleaned:",
    "            cleaned.append(value)",
    "",
    "    return cleaned",
    "",
]

updated = lines[:start] + new_block + lines[end:]

path.write_text(
    '\n'.join(updated) + '\n',
    encoding='utf-8',
)

print('Replaced extract_dimensions_from_html safely')
