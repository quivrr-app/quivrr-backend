import subprocess
import sys

PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/simon_anderson/build_simon_anderson_master_catalogue.py"],
    [PYTHON, "scripts/import_simon_anderson_catalogue.py"],
]

for step in STEPS:
    print("")
    print("=" * 80)
    print("Running:", " ".join(step))
    print("=" * 80)
    result = subprocess.run(step)
    if result.returncode != 0:
        sys.exit(result.returncode)

print("")
print("Simon Anderson catalogue pipeline complete")
