from pathlib import Path

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")

text = path.read_text(encoding="utf-8")

if "\\n" in text:
    text = text.replace("\\n", "\n")

path.write_text(
    text,
    encoding="utf-8",
)

print("Repaired literal newline corruption in Sharp Eye builder")
