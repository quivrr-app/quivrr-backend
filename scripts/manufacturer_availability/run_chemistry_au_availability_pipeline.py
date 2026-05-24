
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

commands = [
    [sys.executable, "scrapers/manufacturers/availability/chemistry/build_chemistry_au_availability.py"],
    [sys.executable, "scripts/manufacturer_availability/import_chemistry_au_availability.py"],
]

for command in commands:
    print("")
    print("=" * 80)
    print("Running:", " ".join(command))
    print("=" * 80)

    result = subprocess.run(command, cwd=ROOT)

    if result.returncode != 0:
        raise SystemExit(result.returncode)

print("")
print("Chemistry AU manufacturer availability pipeline complete")
