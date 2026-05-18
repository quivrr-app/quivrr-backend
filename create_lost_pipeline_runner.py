from pathlib import Path

path = Path("scripts/run_lost_pipeline.py")

content = r'''
import subprocess
import sys


PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/lost/build_lost_master_catalogue.py"],
    [PYTHON, "scripts/import_lost_catalogue.py"],
]


def run_step(command):
    print("")
    print("=" * 80)
    print("Running:", " ".join(command))
    print("=" * 80)
    print("")

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {' '.join(command)}")


def main():
    for step in STEPS:
        run_step(step)

    print("")
    print("Lost catalogue pipeline complete")
    print("")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print(f"Lost catalogue pipeline failed: {exc}")
        print("")
        sys.exit(1)
'''

path.write_text(content.strip() + "\n", encoding="utf-8")
print(f"Created {path}")
