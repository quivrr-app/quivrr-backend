import subprocess
import sys


PYTHON = sys.executable


STEPS = [
    [PYTHON, "scrapers/brands/firewire/build_firewire_master_catalogue.py"],
    [PYTHON, "scripts/import_firewire_catalogue.py"],
]


def main():
    print("")
    print("=" * 80)
    print("FIREWIRE PIPELINE")
    print("=" * 80)

    for step in STEPS:
        print("")
        print("Running:", " ".join(step))

        result = subprocess.run(step)

        if result.returncode != 0:
            raise RuntimeError(f"Pipeline step failed: {' '.join(step)}")

    print("")
    print("Firewire pipeline complete")


if __name__ == "__main__":
    main()
