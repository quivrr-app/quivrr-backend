import unittest

from scrapers.retailers.usa.custom import discover_us_custom_products as custom_discovery


LISTING_HTML = """
<li data-hook="product-list-grid-item">
  <a href="https://www.reddogsurfshop.com/product-page/5-11-mikey-feb-shorty" data-hook="product-item-product-details-link">
    <p data-hook="product-item-name">5'11 Mikey Feb Shorty</p>
  </a>
</li>
<li data-hook="product-list-grid-item">
  <a href="https://www.reddogsurfshop.com/product-page/5-10-f1-squash" data-hook="product-item-product-details-link">
    <p data-hook="product-item-name">5'10 F1 Squash</p>
  </a>
</li>
"""

PRODUCT_HTML = """
<html>
  <head>
    <meta property="og:description" content="18 7/8 x 2 3/8 - 27.6 L Future Tri" />
    <script type="application/ld+json">
      {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "5’11 Mikey Feb Shorty",
        "description": "18 7/8 x 2 3/8 - 27.6 L Future Tri",
        "sku": "1097667",
        "brand": {"@type": "Brand", "name": "CHANNEL ISLANDS"},
        "image": [{"contentUrl": "https://static.example.com/board.png"}],
        "Offers": {
          "@type": "Offer",
          "url": "https://www.reddogsurfshop.com/product-page/5-11-mikey-feb-shorty",
          "priceCurrency": "USD",
          "price": "800",
          "Availability": "https://schema.org/InStock"
        }
      }
    </script>
  </head>
</html>
"""


class UsCustomRetailerDiscoveryTests(unittest.TestCase):
    def test_parse_listing_handles_extracts_unique_product_urls(self):
        handles = custom_discovery.parse_listing_handles(LISTING_HTML)
        self.assertEqual(
            handles,
            [
                "https://www.reddogsurfshop.com/product-page/5-10-f1-squash",
                "https://www.reddogsurfshop.com/product-page/5-11-mikey-feb-shorty",
            ],
        )

    def test_parse_product_json_ld_returns_importable_row(self):
        target = {
            "retailerSlug": "reddog_surf_shop",
            "retailerName": "Reddog Surf Shop",
            "regionCode": "US",
            "country": "United States",
            "platform": "custom_wix_board_inventory",
            "priceCurrency": "USD",
        }
        row = custom_discovery.parse_product_json_ld(
            PRODUCT_HTML,
            "https://www.reddogsurfshop.com/product-page/5-11-mikey-feb-shorty",
            target,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["brand"], "CHANNEL ISLANDS")
        self.assertEqual(row["priceAmount"], "800")
        self.assertEqual(row["stockStatus"], "in_stock")
        self.assertEqual(row["lengthFeetInches"], "5'11")
        self.assertAlmostEqual(row["volumeLitres"], 27.6)


if __name__ == "__main__":
    unittest.main()
