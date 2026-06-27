import unittest

from scripts import import_js_catalogue
from scrapers.brands.js import scrape_js_product_pages


class ExistingSizeRow:
    def __init__(
        self,
        model_id,
        length,
        width,
        thickness,
        volume,
        construction,
        fin_setup,
        tail_shape,
    ):
        self.BoardModelId = model_id
        self.LengthFeetInches = length
        self.Width = width
        self.Thickness = thickness
        self.VolumeLitres = volume
        self.Construction = construction
        self.FinSetup = fin_setup
        self.TailShape = tail_shape


class ImportJsCatalogueTests(unittest.TestCase):
    def test_partition_new_size_rows_skips_existing_exact_signature(self):
        existing_rows = [
            ExistingSizeRow(101, "5'8", "19 1/2", "2 7/16", 29.3, "PU", "FCS II", "Squash")
        ]
        incoming_rows = [
            {
                "model_id": 101,
                "length": "5'8",
                "width": "19 1/2",
                "thickness": "2 7/16",
                "volume": "29.30",
                "construction": "PU",
                "fin_setup": "FCS II",
                "tail_shape": "Squash",
            },
            {
                "model_id": 101,
                "length": "5'9",
                "width": "19 3/4",
                "thickness": "2 1/2",
                "volume": 30.5,
                "construction": "PU",
                "fin_setup": "FCS II",
                "tail_shape": "Squash",
            },
        ]

        rows_to_insert = import_js_catalogue.partition_new_size_rows(
            existing_rows,
            incoming_rows,
        )

        self.assertEqual(len(rows_to_insert), 1)
        self.assertEqual(rows_to_insert[0]["length"], "5'9")

    def test_normalise_volume_collapses_equivalent_decimal_strings(self):
        self.assertEqual(import_js_catalogue.normalise_volume("29.30"), "29.3")
        self.assertEqual(import_js_catalogue.normalise_volume(29.300), "29.3")
        self.assertIsNone(import_js_catalogue.normalise_volume(None))

    def test_js_incomplete_guard_message_includes_expected_and_actual_counts(self):
        message = scrape_js_product_pages.build_incomplete_error_message(
            failures=0,
            expected_models=30,
            scraped_models=10,
            missing_models=20,
        )

        self.assertIn("Failures=0", message)
        self.assertIn("ExpectedModels=30", message)
        self.assertIn("ActualModels=10", message)
        self.assertIn("MissingModels=20", message)

    def test_build_catalogue_models_accepts_placeholder_only_rows_for_model_coverage(self):
        models = import_js_catalogue.build_catalogue_models(
            [
                {
                    "model": "Golden Child",
                    "product_url": "https://jsindustries.com/products/golden-child",
                    "official_image_url": "https://cdn.example/golden-child.jpg",
                    "description": "Official JS description",
                    "board_category": "shortboard",
                    "length": None,
                }
            ],
            [],
        )

        self.assertEqual(list(models.keys()), ["Golden Child"])
        self.assertEqual(models["Golden Child"]["product_url"], "https://jsindustries.com/products/golden-child")
        self.assertEqual(models["Golden Child"]["official_image_url"], "https://cdn.example/golden-child.jpg")
        self.assertEqual(models["Golden Child"]["description"], "Official JS description")
        self.assertEqual(models["Golden Child"]["board_category"], "shortboard")


if __name__ == "__main__":
    unittest.main()
