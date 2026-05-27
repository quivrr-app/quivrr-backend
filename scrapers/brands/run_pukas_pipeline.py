import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

result = subprocess.run(
    [sys.executable, "scripts/run_pukas_pipeline.py"],
    cwd=ROOT,
    text=True,
)

sys.exit(result.returncode)
