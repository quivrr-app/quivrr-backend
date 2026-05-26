import subprocess
import sys

COMMANDS = [
    [sys.executable, "scrapers/manufacturers/availability/misfit/build_misfit_au_availability.py"],
    [sys.executable, "scripts/manufacturer_availability/import_misfit_au_availability.py"],
]

for command in COMMANDS:
    print("")
    print("=" * 80)
    print("Running:", " ".join(command))
    print("=" * 80)

    result = subprocess.run(command)

    if result.returncode != 0:
        raise SystemExit(result.returncode)

print("")
print("Misfit Shapes AU manufacturer availability pipeline complete")
