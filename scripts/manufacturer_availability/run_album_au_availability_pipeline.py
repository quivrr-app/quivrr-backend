import subprocess
import sys

PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/manufacturers/availability/album/build_album_au_availability.py"],
    [PYTHON, "scripts/manufacturer_availability/import_album_au_availability.py"],
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
print("Album AU manufacturer availability pipeline complete")
