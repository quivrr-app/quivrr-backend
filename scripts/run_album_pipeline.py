import subprocess
import sys

PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/album/build_album_master_catalogue.py"],
    [PYTHON, "scripts/import_album_catalogue.py"],
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
print("Album pipeline complete")
