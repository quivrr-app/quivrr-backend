from pathlib import Path

path = Path("scripts/import_chilli_catalogue.py")

path.write_text(r'''
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.import_brand_catalogue_common import import_catalogue


if __name__ == "__main__":

    import_catalogue(
        brand_name="Chilli",
        catalogue_path="scrapers/brands/chilli/output/chilli_master_catalogue_clean.json",
    )
'''.strip() + "\n", encoding="utf-8")

print("Repaired scripts/import_chilli_catalogue.py")
