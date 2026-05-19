from pathlib import Path

path = Path("scripts/run_manufacturer_catalogue_refresh.py")

text = path.read_text(encoding="utf-8")

needle = '("Sharp Eye", "scripts/import_sharpeye_catalogue.py"),'

replacement = '''("Sharp Eye", "scripts/import_sharpeye_catalogue.py"),
    ("Chilli", "scripts/import_chilli_catalogue.py"),'''

if replacement in text:
    print("Chilli already wired into nightly manufacturer refresh")
else:
    if needle not in text:
        raise RuntimeError("Could not find Sharp Eye entry")

    text = text.replace(
        needle,
        replacement,
        1,
    )

    path.write_text(text, encoding="utf-8")

    print("Added Chilli to nightly manufacturer refresh")
