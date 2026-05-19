from pathlib import Path
import re

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")

text = path.read_text(encoding="utf-8")

replacement = r'''
def extract_dimensions_from_html(product_url):
    response = requests.get(
        product_url,
        headers=HEADERS,
        timeout=(10, 30),
    )

    soup = BeautifulSoup(response.text, "html.parser")

    visible_text = soup.get_text(" ", strip=True)

    visible_text = visible_text.replace("×", "x")
    visible_text = visible_text.replace('"', "")
    visible_text = visible_text.replace("”", "")
    visible_text = visible_text.replace("″", "")

    matches = re.findall(
        r"(\d+'\s*\d{1,2}\s*x\s*\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s*L)",
        visible_text,
        flags=re.IGNORECASE,
    )

    cleaned = []

    for match in matches:
        value = clean(match)

        if value not in cleaned:
            cleaned.append(value)

    return cleaned


'''

pattern = r"def extract_dimensions_from_html\(product_url\):.*?return sorted\(set\(cleaned\)\)\n"

updated, count = re.subn(
    pattern,
    replacement,
    text,
    count=1,
    flags=re.DOTALL,
)

if count != 1:
    raise RuntimeError("Could not replace extract_dimensions_from_html")

path.write_text(updated, encoding="utf-8")

print("Replaced Sharp Eye HTML dimension parser with BeautifulSoup text parser")
