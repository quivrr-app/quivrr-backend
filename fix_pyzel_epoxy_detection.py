from pathlib import Path

path = Path("scrapers/brands/pyzel/build_pyzel_master_catalogue.py")
text = path.read_text(encoding="utf-8")

old = '''    if "electralite" in text or "eps" in text:
        return "EPS"
'''

new = '''    if (
        "electralite" in text
        or "electralite plus" in text
        or "eps" in text
        or "epoxy" in text
    ):
        return "EPS"
'''

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("Updated Pyzel EPS detection")
