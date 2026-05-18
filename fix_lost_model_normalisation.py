from pathlib import Path

path = Path("scrapers/brands/lost/build_lost_master_catalogue.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''def normalise_model_name(value):
    value = clean(value)
''',
'''def normalise_model_name(value):
    value = clean(value)

    value = re.sub(r"\\bLib\\s*Tech\\b", "", value, flags=re.I)
    value = re.sub(r"\\bLight\\s*Speed\\s*II\\b", "", value, flags=re.I)
    value = re.sub(r"\\bLightSpeed\\s*II\\b", "", value, flags=re.I)
    value = re.sub(r"\\bLightspeed\\s*II\\b", "", value, flags=re.I)
    value = re.sub(r"\\bLightSpeed\\b", "", value, flags=re.I)
    value = re.sub(r"\\bLightspeed\\b", "", value, flags=re.I)
    value = value.replace("’", "'")
    value = value.replace("Formula-1", "Formula 1")
    value = value.replace("El Patroń", "El Patron")
'''
)

text = text.replace(
'''    return clean(value)
''',
'''    value = re.sub(r"[-_/]+", " ", value)
    value = re.sub(r"\\s+", " ", value).strip()
    return clean(value)
''',
1
)

path.write_text(text, encoding="utf-8")
print("Updated Lost model normalisation")
