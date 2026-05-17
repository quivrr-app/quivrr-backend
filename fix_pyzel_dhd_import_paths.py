from pathlib import Path

files = {}

files["scrapers/brands/pyzel/build_pyzel_master_catalogue.py"] = r'''
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.brands.common_shopify_catalogue import build_catalogue


def main():
    build_catalogue(
        brand_name="Pyzel",
        base_url="https://pyzelsurfboards.com",
        output_file="scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
'''

files["scrapers/brands/dhd/build_dhd_master_catalogue.py"] = r'''
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.brands.common_shopify_catalogue import build_catalogue


def main():
    build_catalogue(
        brand_name="DHD",
        base_url="https://dhdsurf.com",
        output_file="scrapers/brands/dhd/output/dhd_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
'''

files["scripts/import_pyzel_catalogue.py"] = r'''
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_brand_catalogue_common import import_catalogue


def main():
    import_catalogue(
        brand_name="Pyzel",
        catalogue_path="scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
'''

files["scripts/import_dhd_catalogue.py"] = r'''
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_brand_catalogue_common import import_catalogue


def main():
    import_catalogue(
        brand_name="DHD",
        catalogue_path="scrapers/brands/dhd/output/dhd_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
'''

for path, content in files.items():
    file_path = Path(path)
    file_path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Updated {file_path}")
