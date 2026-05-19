import subprocess
import sys


PYTHON = sys.executable


STEPS = [
    [PYTHON, "scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py"],
    [PYTHON, "scripts/import_sharpeye_catalogue.py"],
]


def main():
    print("")
    print("=" * 100)
    print("SHARP EYE PIPELINE")
    print("=" * 100)

    for step in STEPS:
        print("")
        print("Running:", " ".join(step))

        result = subprocess.run(step)

        if result.returncode != 0:
            raise RuntimeError(f"Pipeline step failed: {' '.join(step)}")

    print("")
    print("Sharp Eye pipeline complete")


if __name__ == "__main__":
    main()
