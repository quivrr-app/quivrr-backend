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
