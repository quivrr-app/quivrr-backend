from pathlib import Path

FILE = Path("scrapers/products/daily_inventory_refresh.py")

text = FILE.read_text(encoding="utf-8")

old = '''STEPS = [
    "scrapers/products/shopify_scraper.py",
    "scrapers/products/filter_surfboards.py",
    "scrapers/products/normalise_surfboards.py",
    "scrapers/products/build_grouped_inventory_index.py",
    "scrapers/products/inventory_quality_report.py"
]'''

new = '''STEPS = [
    "scrapers/products/shopify_scraper.py",
    "scrapers/products/woocommerce_scraper.py",
    "scrapers/products/filter_surfboards.py",
    "scrapers/products/normalise_surfboards.py",
    "scrapers/products/build_grouped_inventory_index.py",
    "scrapers/products/inventory_quality_report.py"
]'''

if old not in text:
    raise SystemExit("Could not find the existing STEPS block. No changes made.")

text = text.replace(old, new)

FILE.write_text(text, encoding="utf-8")

print("Updated daily_inventory_refresh.py to include WooCommerce scraper.")
