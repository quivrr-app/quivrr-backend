from pathlib import Path

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")

text = path.read_text(encoding="utf-8")

text = text.replace(
    'value = value.replace("\\\\"", "")',
    'value = value.replace(\'"\', "")'
)

path.write_text(text, encoding="utf-8")

print("Fixed Sharp Eye quote escaping")
