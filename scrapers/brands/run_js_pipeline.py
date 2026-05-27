import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

STEPS = [
    {
        "name": "Scrape JS product pages and dimensions",
        "command": [
            sys.executable,
            "scrapers/brands/js/scrape_js_product_pages.py",
        ],
    },
    {
        "name": "Import JS catalogue into SQL",
        "command": [
            sys.executable,
            "scripts/import_js_catalogue.py",
        ],
    },
]


def run_step(step):
    print("")
    print("=" * 80)
    print(step["name"])
    print("=" * 80)

    result = subprocess.run(
        step["command"],
        cwd=ROOT,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Step failed: {step['name']}"
        )


def main():
    print("")
    print("Starting JS Industries manufacturer catalogue refresh")
    print("")

    for step in STEPS:
        run_step(step)

    print("")
    print("JS Industries manufacturer catalogue refresh complete")
    print("")


if __name__ == "__main__":
    main()
