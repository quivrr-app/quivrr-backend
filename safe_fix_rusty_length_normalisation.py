from pathlib import Path

path = Path("scrapers/brands/rusty/build_rusty_master_catalogue.py")

text = path.read_text(encoding="utf-8")

start = text.index("def normalise_length(value):")
end = text.index("def normalise_fin(value):")

replacement = '''def normalise_length(value):
    value = clean(value)

    value = value.replace("''", '"')
    value = value.replace("”", '"')
    value = value.replace("″", '"')
    value = value.replace('"', "")
    value = value.replace("’", "'")
    value = value.replace("`", "'")

    suffixes = [
        "standard",
        "extra",
        "mint",
        "blue",
        "green",
        "light green",
        "pastel green",
    ]

    lowered = value.lower()

    for suffix in suffixes:

        if lowered.endswith(" " + suffix):
            value = value[:-(len(suffix) + 1)]

        elif lowered.endswith(suffix):
            value = value[:-len(suffix)]

    value = clean(value)

    return value


'''

updated = text[:start] + replacement + text[end:]

path.write_text(updated, encoding="utf-8")

print("Successfully updated normalise_length")
