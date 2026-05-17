import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PIPELINES = [
    {
        "name": "Channel Islands",
        "command": [
            sys.executable,
            "scrapers/brands/channel_islands/run_ci_pipeline.py",
        ],
    },
    {
        "name": "JS Industries",
        "command": [
            sys.executable,
            "scrapers/brands/run_js_pipeline.py",
        ],
    },
]


def run_pipeline(pipeline):
    print("")
    print("#" * 100)
    print(f"RUNNING: {pipeline['name']}")
    print("#" * 100)

    result = subprocess.run(
        pipeline["command"],
        cwd=ROOT,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Pipeline failed: {pipeline['name']}"
        )


def main():
    print("")
    print("Starting weekly manufacturer catalogue refresh")
    print("")

    for pipeline in PIPELINES:
        run_pipeline(pipeline)

    print("")
    print("Weekly manufacturer catalogue refresh complete")
    print("")


if __name__ == "__main__":
    main()
