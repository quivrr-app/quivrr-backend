import unittest

from scripts.usa.us_link_projection_rules import (
    excluded_product_type,
    normalise_brand_and_model_for_projection,
)


class UsLinkProjectionRulesTests(unittest.TestCase):
    def test_degree_33_house_brand_and_model_cleanup(self):
        brand, model, reasons = normalise_brand_and_model_for_projection(
            {
                "retailerSlug": "degree_33_surfboards",
                "brandName": "Domestic",
                "modelName": "\" All Terrain Vehicle Shortboard (Poly)",
                "rawProductTitle": "5'10\" All Terrain Vehicle Shortboard Surfboard (Poly)",
            }
        )
        self.assertEqual(brand, "Degree 33")
        self.assertEqual(model, "All Terrain Vehicle Shortboard")
        self.assertIn("brand_parsing_issue", reasons)
        self.assertIn("model_parsing_issue", reasons)

    def test_infinity_house_brand_and_model_cleanup(self):
        brand, model, reasons = normalise_brand_and_model_for_projection(
            {
                "retailerSlug": "infinity_surfboards",
                "brandName": "SHRED & SPEED",
                "modelName": "\" RAINBOW CHASER",
                "rawProductTitle": "5'10\" RAINBOW CHASER",
            }
        )
        self.assertEqual(brand, "Infinity")
        self.assertEqual(model, "RAINBOW CHASER")
        self.assertIn("brand_parsing_issue", reasons)
        self.assertIn("model_parsing_issue", reasons)

    def test_walden_house_brand_and_model_cleanup(self):
        brand, model, reasons = normalise_brand_and_model_for_projection(
            {
                "retailerSlug": "walden_surfboards",
                "brandName": "ST",
                "modelName": "Surftech Magic Model SOFTOP 2026",
                "rawProductTitle": "Surftech 9'0 Magic Model SOFTOP 2026",
            }
        )
        self.assertEqual(brand, "Walden")
        self.assertEqual(model, "Magic Model")
        self.assertIn("brand_parsing_issue", reasons)
        self.assertIn("model_parsing_issue", reasons)

    def test_stewart_model_cleanup(self):
        brand, model, reasons = normalise_brand_and_model_for_projection(
            {
                "retailerSlug": "stewart_surfboards",
                "brandName": "Stewart",
                "modelName": "\" CMP ( \", 22 5 8\", 2 5 8\") B#129617",
                "rawProductTitle": "9'0\" CMP (9'0\", 22 5/8\", 2 5/8\") B#129617 EPS",
            }
        )
        self.assertEqual(brand, "Stewart")
        self.assertEqual(model, "CMP")
        self.assertEqual(reasons, ["model_parsing_issue"])

    def test_bing_model_cleanup(self):
        brand, model, reasons = normalise_brand_and_model_for_projection(
            {
                "retailerSlug": "bing_surfboards",
                "brandName": "Bing",
                "modelName": "24998 \" BONZER",
                "rawProductTitle": "24998 7'0\" BONZER BOARDROOM COLLECTION",
            }
        )
        self.assertEqual(brand, "Bing")
        self.assertEqual(model, "BONZER")
        self.assertEqual(reasons, ["model_parsing_issue"])

    def test_excluded_product_type_flags_used_and_kneeboard(self):
        self.assertEqual(
            excluded_product_type({"rawProductTitle": "Lost Surfboard 5'7 23L (USED)"}),
            "used_board",
        )
        self.assertEqual(
            excluded_product_type({"rawProductTitle": "6'2 Mojo Kneeboard # 25734"}),
            "kneeboard",
        )


if __name__ == "__main__":
    unittest.main()
