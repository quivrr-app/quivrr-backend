import subprocess
import sys

COMMANDS = [
    [sys.executable, "scrapers/manufacturers/availability/lost/build_lost_au_availability.py"],
    [sys.executable, "scripts/manufacturer_availability/import_lost_au_availability.py"],
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
print("Lost AU manufacturer availability pipeline complete")
