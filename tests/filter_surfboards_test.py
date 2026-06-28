import unittest

from scrapers.products.filter_surfboards import score_item


class FilterSurfboardsTests(unittest.TestCase):
    def test_used_supported_brand_with_compact_length_is_accepted(self):
        item = {
            "title": "Second Al Merrick Sampler 55",
            "variant_title": "Default Title",
            "vendor": "Almerrick",
            "product_type": "SBJ",
            "price": "650.00",
            "product_url": "https://example.com/products/second-al-merrick-sampler-55",
        }

        result = score_item(item)

        self.assertTrue(result["is_surfboard"])
        self.assertIn("brand", result["reasons"])
        self.assertIn("compact_length", result["reasons"])
        self.assertIn("used_board_listing", result["reasons"])

    def test_used_listing_without_board_identity_is_rejected(self):
        item = {
            "title": "Second mystery thing 55",
            "variant_title": "Default Title",
            "vendor": "Unknown",
            "product_type": "SBJ",
            "price": "650.00",
            "product_url": "https://example.com/products/second-mystery-thing-55",
        }

        result = score_item(item)

        self.assertFalse(result["is_surfboard"])
        self.assertEqual(
            result["reject_reason"],
            "low_confidence_or_missing_board_identity",
        )


if __name__ == "__main__":
    unittest.main()
