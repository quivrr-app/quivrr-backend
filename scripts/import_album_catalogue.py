from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.import_brand_catalogue_common import import_catalogue


if __name__ == "__main__":

    import_catalogue(
        brand_name="Album",
        catalogue_path="scrapers/brands/album/output/album_master_catalogue_clean.json",
    )
