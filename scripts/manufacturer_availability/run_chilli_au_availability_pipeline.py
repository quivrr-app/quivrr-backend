import subprocess
import sys

COMMANDS = [
    [sys.executable, "scrapers/manufacturers/availability/chilli/build_chilli_au_availability.py"],
    [sys.executable, "scripts/manufacturer_availability/import_chilli_au_availability.py"],
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
print("Chilli AU manufacturer availability pipeline complete")
