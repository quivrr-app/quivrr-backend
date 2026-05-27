from import_brand_catalogue_common import import_catalogue


def main():
    import_catalogue(
        brand_name="Chemistry Surfboards",
        catalogue_path="scrapers/brands/chemistry/output/chemistry_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
