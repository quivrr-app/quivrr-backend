import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable

STEPS = [
    [
        PYTHON,
        "scrapers/manufacturers/availability/channel_islands/build_ci_au_availability.py",
    ],
    [
        PYTHON,
        "scripts/manufacturer_availability/import_ci_au_availability.py",
    ],
]

for step in STEPS:
    print("")
    print("=" * 80)
    print("Running:", " ".join(step))
    print("=" * 80)

    result = subprocess.run(step)

    if result.returncode != 0:
        raise SystemExit(result.returncode)

print("")
print("Channel Islands AU manufacturer availability pipeline complete")
