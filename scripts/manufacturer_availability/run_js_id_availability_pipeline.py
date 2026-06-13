import subprocess
import sys

PYTHON = sys.executable

steps = [
    [PYTHON, "scrapers/manufacturers/availability/js_industries/build_js_id_availability.py"],
    [PYTHON, "scripts/manufacturer_availability/import_js_id_availability.py"],
]

for step in steps:
    print("Running:", " ".join(step))
    result = subprocess.run(step)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

print("JS Indonesia manufacturer availability pipeline complete")
