from pathlib import Path
import subprocess
import sys

FILTER_FILE = Path("scrapers/products/filter_surfboards.py")

NEW_EXCLUSIONS = [
    '"sock"',
    '"board sock"',
    '"stretch cover"',
    '"cover"',
    '"board bag"',
    '"day bag"',
    '"travel bag"',
    '"coffin"',
    '"accessory"',
    '"accessories"',
    '"strap"',
    '"tie down"',
    '"roof rack"',
    '"rack"',
    '"wall rack"',
    '"board sling"'
]

text = FILTER_FILE.read_text(encoding="utf-8")

insert_after = '"poncho"'

if '"board sock"' not in text:
    replacement = insert_after + ",\n    " + ",\n    ".join(NEW_EXCLUSIONS)
    text = text.replace(insert_after, replacement)
    FILTER_FILE.write_text(text, encoding="utf-8")
    print("Updated filter_surfboards.py exclusions")
else:
    print("Exclusions already present")

steps = [
    "scrapers/products/filter_surfboards.py",
    "scrapers/products/normalise_surfboards.py",
    "scrapers/products/build_grouped_inventory_index.py"
]

for step in steps:
    print("")
    print(f"Running {step}")
    result = subprocess.run([sys.executable, step])

    if result.returncode != 0:
        raise SystemExit(f"Failed: {step}")

print("")
print("Done")
