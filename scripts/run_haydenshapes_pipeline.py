import subprocess
import sys


PYTHON = sys.executable


STEPS = [
    [PYTHON, "scrapers/brands/haydenshapes/build_haydenshapes_master_catalogue.py"],
    [PYTHON, "scripts/import_haydenshapes_catalogue.py"],
]


def main():
    print("")
    print("=" * 100)
    print("HAYDENSHAPES PIPELINE")
    print("=" * 100)

    for step in STEPS:
        print("")
        print("Running:", " ".join(step))

        result = subprocess.run(step)

        if result.returncode != 0:
            raise RuntimeError(f"Pipeline step failed: {' '.join(step)}")

    print("")
    print("Haydenshapes pipeline complete")


if __name__ == "__main__":
    main()
