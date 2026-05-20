import subprocess
import sys

PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/pukas/build_pukas_master_catalogue.py"],
    [PYTHON, "scripts/import_pukas_catalogue.py"],
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
print("Pukas catalogue pipeline complete")
