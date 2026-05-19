import subprocess
import sys

PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/christenson/discover_christenson_model_links.py"],
    [PYTHON, "scrapers/brands/christenson/probe_christenson_dimensions.py"],
    [PYTHON, "scrapers/brands/christenson/build_christenson_master_catalogue.py"],
    [PYTHON, "scripts/import_christenson_catalogue.py"],
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
print("Christenson pipeline complete")
