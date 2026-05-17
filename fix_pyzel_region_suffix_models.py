from pathlib import Path

path = Path("scrapers/brands/common_shopify_catalogue.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
r'''    title = re.sub(r"\b(CA|HI|AU)\s*ID\s*:?\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\bID\s*:?\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\(\s*\d{4,}\s*\)", "", title)
''',
r'''    title = re.sub(r"\b(CA|HI|AU)\s*ID\s*:?\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\bID\s*:?\s*\d+\b", "", title, flags=re.I)
    title = re.sub(r"\(\s*\d{4,}\s*\)", "", title)

    # Pyzel uses CA and HI as regional stock labels in product titles.
    # These should not become separate model names in the guided search.
    title = re.sub(r"\b(CA|HI|AU)\b$", "", title, flags=re.I)
    title = re.sub(r"\b(CA|HI|AU)\b", "", title, flags=re.I)
'''
)

path.write_text(text, encoding="utf-8")
print("Updated Pyzel model name cleanup in common_shopify_catalogue.py")
