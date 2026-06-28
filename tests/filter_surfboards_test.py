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

    def test_rental_listing_is_rejected_even_when_board_terms_exist(self):
        item = {
            "title": "Album Bom Dia Surfboard Hire 5'6",
            "variant_title": "Daily rental",
            "vendor": "Album",
            "product_type": "Surfboards",
            "price": "85.00",
            "product_url": "https://example.com/products/album-bom-dia-surfboard-hire-56",
        }

        result = score_item(item)

        self.assertFalse(result["is_surfboard"])
        self.assertEqual(
            result["reject_reason"],
            "service_or_rental_listing",
        )

    def test_service_listing_is_rejected_even_when_supported_brand_exists(self):
        item = {
            "title": "Channel Islands Board Repair Service",
            "variant_title": "Default Title",
            "vendor": "Channel Islands",
            "product_type": "Surfboards",
            "price": "450.00",
            "product_url": "https://example.com/products/channel-islands-board-repair-service",
        }

        result = score_item(item)

        self.assertFalse(result["is_surfboard"])
        self.assertEqual(
            result["reject_reason"],
            "service_or_rental_listing",
        )


if __name__ == "__main__":
    unittest.main()
