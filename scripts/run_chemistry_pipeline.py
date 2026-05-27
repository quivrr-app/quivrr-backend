import subprocess
import sys

PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/chemistry/build_chemistry_master_catalogue.py"],
    [PYTHON, "scripts/import_chemistry_catalogue.py"],
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
print("Chemistry catalogue pipeline complete")
