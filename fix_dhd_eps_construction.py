from pathlib import Path

path = Path("scrapers/brands/dhd/build_dhd_master_catalogue.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''def normalise_construction(model, source_title):
    text = clean_text(f"{model} {source_title}")

    if "eps" in text:
        return "EPS"

    if "soft top" in text:
        return "Soft Top"

    return "PU"
''',
'''def normalise_construction(model, source_title, source_product_title, product_url):
    text = clean_text(f"{model} {source_title} {source_product_title} {product_url}")

    if "eps" in text:
        return "EPS"

    if "soft top" in text:
        return "Soft Top"

    return "PU"
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
'''        row["construction"] = normalise_construction(model, source_title, source_product_title, product_url)
'''
)

path.write_text(text, encoding="utf-8")
print("Updated DHD EPS construction handling")
