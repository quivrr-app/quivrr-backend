import unittest
from unittest.mock import Mock, patch

import requests

from scrapers.manufacturers.availability.dhd.build_dhd_eu_availability import (
    dimensions as dhd_dimensions,
    model_name as dhd_model_name,
)
from scrapers.manufacturers.availability.eu.build_eu_shopify_availability import (
    construction,
    model_name,
)
from scrapers.retailers.europe.shopify.discover_eu_shopify_products import (
    fetch_products,
)


class EuMfaModelNormalisationTests(unittest.TestCase):
    def test_js_x_series_is_a_construction_variant(self):
        self.assertEqual(
            model_name(
                "JS Industries",
                "JS Surfboard 5'7 XERO FUSION X SERIES PU 5ft7",
            ),
            "Xero Fusion",
        )

    def test_js_easy_rider_tail_and_colour_suffixes(self):
        self.assertEqual(
            model_name(
                "JS Industries",
                "JS Surfboard 5'9 MONSTA SQUASH EASY RIDER PU 5ft9",
            ),
            "Monsta Easy Rider",
        )
        self.assertEqual(
            model_name(
                "JS Industries",
                "JS Surfboard 7'0 BIG BARON TAN PE 7ft0",
            ),
            "Big Baron",
        )

    def test_js_whole_foot_title_prefix(self):
        self.assertEqual(
            model_name(
                "JS Industries",
                "JS Surfboard 6 XERO FUSION X SERIES PU 6ft0",
            ),
            "Xero Fusion",
        )

    def test_js_construction_names_match_au(self):
        self.assertEqual(construction("XERO CARBOTUNE"), "CarboTune")
        self.assertEqual(construction("XERO PE 5ft9"), "PE")
        self.assertEqual(construction("XERO HYFI 3.0"), "HYFI")

    def test_dhd_construction_and_tail_aliases(self):
        self.assertEqual(dhd_model_name("EE JULIETTE RT FCS"), "EE Juliette")
        self.assertEqual(dhd_model_name("UTOPIA EPS FCS"), "Utopia")
        self.assertEqual(
            dhd_model_name("PHOENIX SWALLOW EPS FCS"),
            "Phoenix EPS Swallow Tail",
        )

    def test_dhd_dimensions(self):
        self.assertEqual(
            dhd_dimensions("5'9 - 18 5/8 x 2 5/16 - 26 L"),
            ("5'9", "18 5/8", "2 5/16", 26.0),
        )

    @patch("scrapers.retailers.europe.shopify.discover_eu_shopify_products.time.sleep")
    @patch("scrapers.retailers.europe.shopify.discover_eu_shopify_products.requests.get")
    def test_shopify_transport_retries_and_reports_response(self, get, _sleep):
        response = Mock(
            status_code=200,
            url="https://example.test/collections/boards/products.json",
            content=b'{"products": [{"id": 1}]}',
            headers={"Content-Type": "application/json", "CF-Ray": "test-ray"},
        )
        response.json.return_value = {"products": [{"id": 1}]}
        get.side_effect = [requests.Timeout("cold edge"), response]

        result = fetch_products("https://example.test/collections/boards/products.json")

        self.assertTrue(result["ok"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["responseBytes"], len(response.content))
        self.assertEqual(result["products"], [{"id": 1}])


if __name__ == "__main__":
    unittest.main()
