import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_brand_catalogue_common import import_catalogue


def main():
    import_catalogue(
        brand_name="Sharp Eye",
        catalogue_path="scrapers/brands/sharpeye/output/sharpeye_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
