import unittest

from scripts.europe.import_eu_retailer_inventory import (
    extract_canonical_brand_name,
    extract_model_hint,
    select_model_candidate,
    tolerant_model_key,
)


class EuCanonicalLinkingTests(unittest.TestCase):
    def test_tolerant_model_key_maps_safe_eu_aliases(self):
        cases = [
            ("Neck Beard 2", "Neckbeard 2"),
            ("Sabo Taj", "Sabotaj"),
            ("Sword Fish", "Swordfish"),
            ("Water Hog", "Waterhog"),
            ("Spud Nick", "Spudnick"),
            ("421", "421 Fish"),
            ("WhiteTiger", "White Tiger"),
            ("California Twin", "Cali Twin"),
            ("Juliette", "EE Juliette"),
            ("Black and White", "Black/White"),
        ]
        for retailer_model, canonical_model in cases:
            with self.subTest(retailer_model=retailer_model):
                self.assertEqual(
                    tolerant_model_key(retailer_model),
                    tolerant_model_key(canonical_model),
                )

    def test_select_model_candidate_uses_tolerant_alias_match(self):
        models_by_brand = {
            1: [
                {"boardModelId": 10, "brandId": 1, "modelName": "Neckbeard 2", "modelKey": "neckbeard 2"},
                {"boardModelId": 11, "brandId": 1, "modelName": "Sabotaj", "modelKey": "sabotaj"},
                {"boardModelId": 12, "brandId": 1, "modelName": "421 Fish", "modelKey": "421 fish"},
            ]
        }
        cases = [
            ("Surfboard Channel Island Neck Beard 2 - 5'6", "Neckbeard 2"),
            ("Surfboard Lost Sabo Taj - 5'6", "Sabotaj"),
            ("RUSTY Surfboard 421 - 5'10", "421 Fish"),
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                selected = select_model_candidate(
                    {
                        "brandId": 1,
                        "rawProductTitle": title,
                        "normalisedProductTitle": title,
                    },
                    models_by_brand,
                )
                self.assertIsNotNone(selected)
                self.assertEqual(selected["modelName"], expected)

    def test_select_model_candidate_accepts_clear_score_gap(self):
        models_by_brand = {
            1: [
                {"boardModelId": 20, "brandId": 1, "modelName": "Happy", "modelKey": "happy"},
                {"boardModelId": 21, "brandId": 1, "modelName": "Happy Everyday", "modelKey": "happy everyday"},
            ]
        }
        selected = select_model_candidate(
            {
                "brandId": 1,
                "brandName": "Channel Islands",
                "rawProductTitle": "Channel Islands Happy Everyday",
                "normalisedProductTitle": "Channel Islands Happy Everyday",
                "parsedModel": "Happy Everyday",
            },
            models_by_brand,
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected["modelName"], "Happy Everyday")
        self.assertFalse(selected["ambiguous"])
        self.assertGreaterEqual(selected["scoreGap"], 2500)

    def test_extract_model_hint_strips_used_prefix_length_and_stock_codes(self):
        self.assertEqual(
            extract_model_hint(
                "5'11 JS Xero Gravity Carbotune #8057 - Used Surfboard",
                "JS Industries",
            ),
            "Xero Gravity",
        )
        self.assertEqual(
            extract_model_hint(
                "USED Lost Driver 3.0 Grom PU/Poly 5'9\"",
                "Lost",
            ),
            "Driver 3.0 Grom",
        )

    def test_extract_canonical_brand_name_supports_supported_brand_aliases_after_prefix_cleanup(self):
        self.assertEqual(
            extract_canonical_brand_name(
                "USED SimonAnderson Holy Grail 6'1",
                "",
            ),
            "Simon Anderson",
        )
        self.assertEqual(
            extract_canonical_brand_name(
                "5'8 Chemistry Surfboards Zen 3",
                "",
            ),
            "Chemistry Surfboards",
        )


if __name__ == "__main__":
    unittest.main()
