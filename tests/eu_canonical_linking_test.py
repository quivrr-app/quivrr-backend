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
            ("Sweetspot", "Sweet Spot 4.0"),
            ("Juliette", "EE Juliette"),
            ("Machado Cado", "Machadocado"),
            ("Mini Driver", "Mini Driver (Re Issue)"),
            ("California Twin", "Cali Twin"),
            ("Hypto Twin", "Hypto Krypto Twin"),
            ("Mikey Febs Fish", "Feb's Fish"),
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
                {"boardModelId": 13, "brandId": 1, "modelName": "Mini Driver (Re Issue)", "modelKey": "mini driver re issue"},
                {"boardModelId": 14, "brandId": 1, "modelName": "Cali Twin", "modelKey": "cali twin"},
                {"boardModelId": 15, "brandId": 1, "modelName": "Hypto Krypto Twin", "modelKey": "hypto krypto twin"},
                {"boardModelId": 16, "brandId": 1, "modelName": "Feb's Fish", "modelKey": "feb s fish"},
            ]
        }
        cases = [
            ("Surfboard Channel Island Neck Beard 2 - 5'6", "Neckbeard 2"),
            ("Surfboard Lost Sabo Taj - 5'6", "Sabotaj"),
            ("RUSTY Surfboard 421 - 5'10", "421 Fish"),
            ("Lost Mini Driver - 5'8", "Mini Driver (Re Issue)"),
            ("Lost California Twin - 5'6", "Cali Twin"),
            ("Haydenshapes Hypto Twin - 5'11", "Hypto Krypto Twin"),
            ("Channel Islands Mikey Febs Fish - 5'7", "Feb's Fish"),
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

    def test_select_model_candidate_prefers_clear_top_score_without_false_ambiguity(self):
        models_by_brand = {
            1: [
                {"boardModelId": 10, "brandId": 1, "modelName": "Happy Everyday", "modelKey": "happy everyday"},
                {"boardModelId": 11, "brandId": 1, "modelName": "Happy", "modelKey": "happy"},
            ]
        }
        selected = select_model_candidate(
            {
                "brandId": 1,
                "brandName": "Channel Islands",
                "rawProductTitle": "Channel Islands Happy Everyday",
                "normalisedProductTitle": "Channel Islands Happy Everyday",
            },
            models_by_brand,
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected["modelName"], "Happy Everyday")
        self.assertFalse(selected["ambiguous"])

    def test_select_model_candidate_cleans_trailing_punctuation(self):
        models_by_brand = {
            1: [
                {"boardModelId": 10, "brandId": 1, "modelName": "Dumpster Diver 2", "modelKey": "dumpster diver 2"},
            ]
        }
        selected = select_model_candidate(
            {
                "brandId": 1,
                "brandName": "Channel Islands",
                "rawProductTitle": 'Dumpster Diver 2 - Spine-Tek EPS 5\'8" x 19 1/2" x 2 7/16" - 29.3L',
                "normalisedProductTitle": 'Dumpster Diver 2 - Spine-Tek EPS 5\'8" x 19 1/2" x 2 7/16" - 29.3L',
            },
            models_by_brand,
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected["modelName"], "Dumpster Diver 2")


if __name__ == "__main__":
    unittest.main()
