from pathlib import Path

path = Path("scripts/import_chilli_catalogue.py")

path.write_text(r'''
from scripts.import_brand_catalogue_common import import_catalogue


if __name__ == "__main__":

    import_catalogue(
        brand_name="Chilli",
        catalogue_path="scrapers/brands/chilli/output/chilli_master_catalogue_clean.json",
    )
'''.strip() + "\n", encoding="utf-8")

print("Created scripts/import_chilli_catalogue.py")
