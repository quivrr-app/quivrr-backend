from pathlib import Path

pipeline_path = Path("scripts/run_rusty_pipeline.py")

pipeline_content = r'''
import subprocess
import sys


PYTHON = sys.executable


STEPS = [
    [PYTHON, "scrapers/brands/rusty/build_rusty_master_catalogue.py"],
    [PYTHON, "scripts/import_rusty_catalogue.py"],
]


def main():

    print("")
    print("=" * 80)
    print("RUSTY PIPELINE")
    print("=" * 80)

    for step in STEPS:

        print("")
        print("Running:", " ".join(step))

        result = subprocess.run(step)

        if result.returncode != 0:
            raise RuntimeError(f"Pipeline step failed: {' '.join(step)}")

    print("")
    print("Rusty pipeline complete")


if __name__ == "__main__":
    main()
'''

pipeline_path.write_text(
    pipeline_content.strip() + "\n",
    encoding="utf-8",
)

print(f"Created {pipeline_path}")
