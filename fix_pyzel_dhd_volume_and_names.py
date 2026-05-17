from pathlib import Path

path = Path("scrapers/brands/common_shopify_catalogue.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
r'''def find_volume(value):
    value = clean(value)

    if not value:
        return None

    match = VOLUME_RE.search(value)

    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None
''',
r'''def find_volume(value):
    value = clean(value)

    if not value:
        return None

    numeric_only = re.fullmatch(r"\d{2}(?:\.\d+)?", value)

    if numeric_only:
        try:
            return float(value)
        except ValueError:
            return None

    match = VOLUME_RE.search(value)

    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None
'''
)

text = text.replace(
r'''def strip_size_noise(title):
    title = clean(title) or ""
    title = SIZE_LINE_RE.sub("", title)
    title = VOLUME_RE.sub("", title)
    title = LENGTH_ONLY_RE.sub("", title)
    title = re.sub(r"\b(FCS II|FCS2|FCS|Futures|Future|Thruster|Quad|Twin|5 Fin)\b", "", title, flags=re.I)
    title = re.sub(r"\b(PU|PE|EPS|Epoxy|Electralite|FutureFlex|Carbon Wrap|Carbon|Dark Arts|Phantom Phlex)\b", "", title, flags=re.I)
    title = re.sub(r"[-|_/]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()

    return title
''',
r'''def strip_size_noise(title):
    title = clean(title) or ""
    title = SIZE_LINE_RE.sub("", title)
    title = VOLUME_RE.sub("", title)
    title = LENGTH_ONLY_RE.sub("", title)
    title = re.sub(r"\b(FCS II|FCS2|FCS|Futures|Future|Thruster|Quad|Twin|5 Fin)\b", "", title, flags=re.I)
    title = re.sub(r"\b(PU|PE|EPS|Epoxy|Electralite|FutureFlex|Carbon Wrap|Carbon|Dark Arts|Phantom Phlex)\b", "", title, flags=re.I)

    title = re.sub(r"\bx\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\b(new board|used board|factory 2nd|demo)\b", "", title, flags=re.I)
    title = re.sub(r"\b(CA|HI|AU)\s*ID\s*:?\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\bID\s*:?\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\(\s*\d{4,}\s*\)", "", title)

    title = re.sub(r"[-|_/]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()

    return title
'''
)

path.write_text(text, encoding="utf-8")
print("Updated scrapers/brands/common_shopify_catalogue.py")
