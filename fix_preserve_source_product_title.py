from pathlib import Path

path = Path("scrapers/brands/common_shopify_catalogue.py")
text = path.read_text(encoding="utf-8")

if '"source_product_title": title,' not in text:
    text = text.replace(
'''                    "source_product_id": product.get("id"),
                    "source_variant_id": variant.get("id"),''',
'''                    "source_product_title": title,
                    "source_product_id": product.get("id"),
                    "source_variant_id": variant.get("id"),'''
    )

path.write_text(text, encoding="utf-8")
print("Updated common_shopify_catalogue.py to preserve source_product_title")
