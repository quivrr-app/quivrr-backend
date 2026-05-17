import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


STEPS = [
    {
        "name": "Build CI canonical model links",
        "command": [
            sys.executable,
            "scrapers/brands/channel_islands/build_ci_canonical_model_links.py",
        ],
    },
    {
        "name": "Build CI master catalogue",
        "command": [
            sys.executable,
            "scrapers/brands/channel_islands/build_ci_master_catalogue.py",
        ],
    },
    {
        "name": "Normalise CI master catalogue",
        "command": [
            sys.executable,
            "scrapers/brands/channel_islands/normalise_ci_master_catalogue.py",
        ],
    },
    {
        "name": "Import CI catalogue into SQL",
        "command": [
            sys.executable,
            "scripts/import_ci_catalogue.py",
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
    print("Starting Channel Islands manufacturer catalogue refresh")
    print("")

    for step in STEPS:
        run_step(step)

    print("")
    print("Channel Islands manufacturer catalogue refresh complete")
    print("")


if __name__ == "__main__":
    main()
