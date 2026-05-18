from pathlib import Path

path = Path("scripts/run_all_brand_catalogues.py")

text = path.read_text(encoding="utf-8")

insert_after = """    {
        "name": "Lost",
        "command": [PYTHON, "scripts/run_lost_pipeline.py"],
    },
"""

rusty_block = """    {
        "name": "Rusty",
        "command": [PYTHON, "scripts/run_rusty_pipeline.py"],
    },
"""

updated = text.replace(
    insert_after,
    insert_after + rusty_block,
)

path.write_text(updated, encoding="utf-8")

print("Rusty added to weekly runner")
