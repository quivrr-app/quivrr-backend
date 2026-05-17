from pathlib import Path

path = Path("scrapers/brands/pyzel/build_pyzel_master_catalogue.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''    "Pyzalien 2 XL Electralite",
    "Pyzalien 2 Electralite",
    "Phantom XL Electralite",
    "Phantom Electralite",
    "Mini Ghost Round",
    "Mini Ghost Squash",
''',
'''    "Mini Ghost Round",
    "Mini Ghost Squash",
    "Pyzalien 2 XL",
    "Pyzalien 2",
    "Phantom XL",
    "Phantom",
'''
)

text = text.replace(
'''        source_title = row.get("model") or ""
        model = canonical_model(source_title)
''',
'''        source_title = row.get("model") or ""
        source_product_title = row.get("source_product_title") or ""
        product_url = row.get("official_product_url") or ""
        model_source = " ".join([source_title, source_product_title, product_url])
        model = canonical_model(model_source)
'''
)

text = text.replace(
'''        row["construction"] = normalise_construction(model, source_title)
''',
'''        row["construction"] = normalise_construction(model, " ".join([source_title, source_product_title, product_url]))
'''
)

text = text.replace(
'''    text = re.sub(r"\\b(electralite|eps|pu)\\b", "", text)
''',
'''    text = re.sub(r"\\b(electralite|eps|pu)\\b", "", text)
'''
)

path.write_text(text, encoding="utf-8")
print("Updated Pyzel EPS construction handling")
