from pathlib import Path
import re

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")
text = path.read_text(encoding="utf-8")

new_parse_dimensions = r'''
def parse_dimensions(text_value):
    text_value = clean(text_value)
    text_value = text_value.replace("×", "x")
    text_value = text_value.replace('"', "")
    text_value = text_value.replace("”", "")
    text_value = text_value.replace("″", "")

    pattern = (
        r"(?P<length>\d+'\s*\d{1,2})"
        r"(?:\s*HV)?"
        r"\s*[xX]\s*"
        r"(?P<width>\d+(?:\.\d+)?)"
        r"\s*[xX]\s*"
        r"(?P<thickness>\d+(?:\.\d+)?)"
        r"\s+"
        r"(?P<volume>\d+(?:\.\d+)?)\s*L"
    )

    match = re.search(pattern, text_value, flags=re.IGNORECASE)

    if not match:
        return {
            "length": None,
            "width": None,
            "thickness": None,
            "volume_litres": None,
            "is_hv": " HV " in f" {text_value.upper()} ",
        }

    return {
        "length": clean(match.group("length").replace(" ", "")),
        "width": clean(match.group("width")),
        "thickness": clean(match.group("thickness")),
        "volume_litres": Decimal(match.group("volume")),
        "is_hv": " HV " in f" {text_value.upper()} ",
    }


'''

text, count = re.subn(
    r"def parse_dimensions\(text_value\):.*?\n\ndef first_image",
    new_parse_dimensions + "def first_image",
    text,
    count=1,
    flags=re.DOTALL,
)

if count != 1:
    raise RuntimeError("Could not replace parse_dimensions")

new_extract = r'''
def extract_dimensions_from_html(product_url):
    response = requests.get(
        product_url,
        headers=HEADERS,
        timeout=(10, 30),
    )

    html = response.text
    html = html.replace("&quot;", '"')
    html = html.replace("×", "x")

    matches = re.findall(
        r"(\d+'\s*\d{1,2}\"?\s*x\s*\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s*L)",
        html,
        flags=re.IGNORECASE,
    )

    cleaned = []

    for match in matches:
        cleaned.append(clean(match))

    return sorted(set(cleaned))


'''

text, count = re.subn(
    r"def extract_dimensions_from_html\(product_url\):.*?\n\ndef fetch_products",
    new_extract + "def fetch_products",
    text,
    count=1,
    flags=re.DOTALL,
)

if count != 1:
    raise RuntimeError("Could not replace extract_dimensions_from_html")

path.write_text(text, encoding="utf-8")

print("Rewrote Sharp Eye dimension parsing functions")
