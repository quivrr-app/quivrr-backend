from pathlib import Path

scripts_pipeline = Path("scripts/run_album_pipeline.py")
scripts_pipeline.write_text(r'''
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
'''.strip() + "\n", encoding="utf-8")

brand_wrapper = Path("scrapers/brands/run_album_pipeline.py")
brand_wrapper.write_text(r'''
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

result = subprocess.run(
    [sys.executable, "scripts/run_album_pipeline.py"],
    cwd=ROOT,
    text=True,
)

sys.exit(result.returncode)
'''.strip() + "\n", encoding="utf-8")

runner = Path("scrapers/brands/run_all_brand_catalogues.py")
text = runner.read_text(encoding="utf-8")

if '"name": "Album"' not in text:
    marker = '''    {
        "name": "Chilli",
        "command": [
            sys.executable,
            "scrapers/brands/run_chilli_pipeline.py",
        ],
    },'''

    block = marker + '''

    {
        "name": "Album",
        "command": [
            sys.executable,
            "scrapers/brands/run_album_pipeline.py",
        ],
    },'''

    if marker not in text:
        raise RuntimeError("Could not find Chilli block in weekly runner")

    text = text.replace(marker, block, 1)
    runner.write_text(text, encoding="utf-8")
    print("Added Album to real weekly brand runner")
else:
    print("Album already wired")

print("Created Album pipeline files")
