import unittest

from scripts.europe.import_eu_retailer_inventory import (
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


if __name__ == "__main__":
    unittest.main()
