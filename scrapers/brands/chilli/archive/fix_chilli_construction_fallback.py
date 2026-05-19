from pathlib import Path

path = Path("scrapers/brands/chilli/build_chilli_master_catalogue.py")

text = path.read_text(encoding="utf-8")

old = '''        construction = (
            clean(detail.get("surfboardconstructiontype"))
            or clean(model.get("surfboardconstructiontype"))
            or None
        )'''

new = '''        construction = (
            clean(detail.get("surfboardconstructiontype"))
            or clean(model.get("surfboardconstructiontype"))
            or "Standard"
        )'''

if old not in text:
    raise RuntimeError("Could not find Chilli construction block")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("Updated Chilli fallback construction to Standard")
