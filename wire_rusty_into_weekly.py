from pathlib import Path

path = Path("scripts/run_all_brand_catalogues.py")

text = path.read_text(encoding="utf-8")

needle = """    {
        "name": "DHD",
        "command": [PYTHON, "scripts/run_dhd_pipeline.py"],
        "required": True,
    },
"""

replacement = """    {
        "name": "DHD",
        "command": [PYTHON, "scripts/run_dhd_pipeline.py"],
        "required": True,
    },
    {
        "name": "Rusty",
        "command": [PYTHON, "scripts/run_rusty_pipeline.py"],
        "required": True,
    },
"""

text = text.replace(needle, replacement)

path.write_text(text, encoding="utf-8")

print("Added Rusty to weekly catalogue runner")
