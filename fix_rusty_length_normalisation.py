from pathlib import Path
import re

path = Path("scrapers/brands/rusty/build_rusty_master_catalogue.py")
text = path.read_text(encoding="utf-8")

new_function = r'''def normalise_length(value):
    value = clean(value)

    value = value.replace("''", '"')
    value = value.replace("”", '"')
    value = value.replace("″", '"')
    value = value.replace('"', "")
    value = value.replace("’", "'")
    value = value.replace("`", "'")

    value = re.sub(
        r"\s+(standard|extra|mint|blue|green|light green|pastel green)$",
        "",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"(standard|extra|mint|blue|green|light green|pastel green)$",
        "",
        value,
        flags=re.I,
    )

    value = clean(value)

    return value
'''

text = re.sub(
    r"def normalise_length\(value\):.*?def normalise_fin\(value\):",
    new_function + "\n\ndef normalise_fin(value):",
    text,
    flags=re.S,
)

path.write_text(text, encoding="utf-8")
print("Updated normalise_length in Rusty builder")
