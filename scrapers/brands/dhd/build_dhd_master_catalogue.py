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
