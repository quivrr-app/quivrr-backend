import subprocess
import sys


def main():
    result = subprocess.run(
        [
            sys.executable,
            "-u",
            "scripts/run_nightly_inventory_refresh.py",
        ]
    )

    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
