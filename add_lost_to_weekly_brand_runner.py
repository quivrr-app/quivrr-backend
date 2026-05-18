from pathlib import Path

path = Path("scripts/run_all_brand_catalogues.py")
text = path.read_text(encoding="utf-8")

needle = '''    {
        "name": "DHD",
        "command": [PYTHON, "scripts/run_dhd_pipeline.py"],
    },'''

replacement = '''    {
        "name": "DHD",
        "command": [PYTHON, "scripts/run_dhd_pipeline.py"],
    },
    {
        "name": "Lost",
        "command": [PYTHON, "scripts/run_lost_pipeline.py"],
    },'''

if '"name": "Lost"' not in text:
    text = text.replace(needle, replacement)

path.write_text(text, encoding="utf-8")
print("Updated scripts/run_all_brand_catalogues.py with Lost")
