from pathlib import Path

path = Path("scripts/run_chilli_pipeline.py")

path.write_text(r'''
import subprocess
import sys


PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/chilli/build_chilli_master_catalogue.py"],
    [PYTHON, "scripts/import_chilli_catalogue.py"],
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

print("Fixed scripts/run_chilli_pipeline.py to use venv interpreter")
