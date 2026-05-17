import subprocess
import sys


PYTHON = sys.executable

STEPS = [
    [PYTHON, "scrapers/brands/dhd/build_dhd_master_catalogue.py"],
    [PYTHON, "scripts/import_dhd_catalogue.py"],
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
    print("DHD catalogue pipeline complete")
    print("")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print(f"DHD catalogue pipeline failed: {exc}")
        print("")
        sys.exit(1)
