import unittest

from scrapers.brands.christenson.build_christenson_master_catalogue import (
    christenson_category_from_type,
)


class ChristensonCatalogueBuilderTests(unittest.TestCase):
    def test_category_mapping_uses_expected_type_buckets(self):
        self.assertEqual(christenson_category_from_type("Fish"), "Fish")
        self.assertEqual(christenson_category_from_type("Mid Length"), "Mid Length")
        self.assertEqual(christenson_category_from_type("Longboard"), "Longboard")
        self.assertEqual(christenson_category_from_type("Step Up Gun"), "Step Up")
        self.assertEqual(christenson_category_from_type("Twin"), "Twin")
        self.assertEqual(christenson_category_from_type(None), "Shortboard")


if __name__ == "__main__":
    unittest.main()
