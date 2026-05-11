from pathlib import Path

FILE = Path("scrapers/products/build_js_inventory_index.py")

text = FILE.read_text(encoding="utf-8")

old = '''JS_TERMS = [
    "js industries",
    "js surfboards",
    "js ",
    " monsta",
    " xero",
    " black baron",
    " big baron",
    " raging bull",
    " golden child",
    " sub xero",
    " el baron",
    " red baron",
    " flame fish",
    " bullseye",
    " schooner",
    " forget me not"
]'''

new = '''JS_MODEL_TERMS = [
    "monsta",
    "xero gravity",
    "xero fusion",
    "xero",
    "black baron",
    "big baron",
    "raging bull",
    "golden child",
    "sub xero",
    "el baron",
    "red baron",
    "flame fish",
    "bullseye",
    "schooner",
    "forget me not",
    "monsta box",
    "black box",
    "psycho nitro",
    "air 17",
    "bull run"
]'''

text = text.replace(old, new)

old_func = '''def is_js(item):
    text = clean(" ".join([
        str(item.get("vendor") or ""),
        str(item.get("title") or ""),
        str(item.get("variant_title") or ""),
        str(item.get("sku") or "")
    ]))

    if any(bad in text for bad in BAD_TERMS):
        return False

    return any(term.strip() in text for term in JS_TERMS)
'''

new_func = '''def is_js(item):
    vendor = clean(item.get("vendor"))
    title = clean(item.get("title"))
    variant = clean(item.get("variant_title"))
    sku = clean(item.get("sku"))

    text = " ".join([vendor, title, variant, sku])

    if any(bad in text for bad in BAD_TERMS):
        return False

    vendor_or_title_says_js = (
        "js industries" in vendor
        or vendor == "js"
        or title.startswith("js ")
        or " js " in title
        or "js industries" in title
        or "js surfboards" in title
    )

    known_js_model = any(model in text for model in JS_MODEL_TERMS)

    return vendor_or_title_says_js or known_js_model
'''

if old_func not in text:
    raise SystemExit("Could not find is_js function block. No changes made.")

text = text.replace(old_func, new_func)

FILE.write_text(text, encoding="utf-8")

print("Patched build_js_inventory_index.py with stricter JS matching.")
