from pathlib import Path

path = Path("scripts/run_chilli_pipeline.py")

path.write_text(r'''
import subprocess
import sys


STEPS = [
    ["python", "scrapers/brands/chilli/build_chilli_master_catalogue.py"],
    ["python", "scripts/import_chilli_catalogue.py"],
]


for step in STEPS:

    print("")
    print("=" * 100)
    print("Running:", " ".join(step))
    print("=" * 100)

    result = subprocess.run(step)

    if result.returncode != 0:
        sys.exit(result.returncode)

print("")
print("Chilli pipeline complete")
'''.strip() + "\n", encoding="utf-8")

print("Created scripts/run_chilli_pipeline.py")
