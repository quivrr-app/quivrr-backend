import unittest
import inspect

import app

from utils.dimensions import (
    decimal_measurement,
    dimensions_from_title,
    equivalent_board_dimensions,
    length_to_inches,
    measurements_within,
    volume_to_decimal,
)
from utils.retailer_matching import classify_retailer_exact
from scripts.europe.import_eu_retailer_inventory import (
    batch_update_inventory,
    inventory_key,
    inventory_missing_volume_key,
    select_size_candidate,
)
from scrapers.retailers.europe.magento.discover_eu_magento_products import (
    parse_58surf_product_detail,
)
from scrapers.retailers.europe.normalise_eu_retailer_inventory import normalise_row


class DimensionMatchingTests(unittest.TestCase):
    def test_fraction_and_decimal_inch_normalisation(self):
        self.assertEqual(decimal_measurement("18 3/4"), decimal_measurement("18.75"))
        self.assertTrue(measurements_within("18 3/4", "18.88", "0.15"))
        self.assertTrue(measurements_within("2 7/16", "2.38", "0.08"))
        self.assertEqual(decimal_measurement("20 7/8"), decimal_measurement("20.875"))

    def test_comma_decimal_volume(self):
        self.assertEqual(volume_to_decimal("77,60L"), volume_to_decimal("77.6"))

    def test_listing_title_dimensions_are_shared_with_matching(self):
        self.assertEqual(
            dimensions_from_title("MONSTA 10 - 6'0\" x 18.88 x 2.38 x 28,5L"),
            {"length": "6'0\"", "width": "18.88", "thickness": "2.38", "volume": "28,5"},
        )
        self.assertEqual(
            dimensions_from_title('UTOPIA - 5\'11" x 19" x 2 7/16" - 28.5L'),
            {"length": "5'11\"", "width": "19", "thickness": "2 7/16", "volume": "28.5"},
        )

    def test_length_formats(self):
        for value in ("5'11", "5ft11", "5’11", '5"11'):
            self.assertEqual(length_to_inches(value), 71)
        self.assertEqual(length_to_inches("6'0"), 72)
        self.assertNotEqual(length_to_inches("5'11"), length_to_inches("6'0"))

    def test_equivalent_dimensions_require_exact_length(self):
        canonical = {"length": "5'11", "width": "18 3/4", "thickness": "2 7/16", "volume": 28}
        retailer = {"length": "5ft11", "width": "18.88", "thickness": "2.38", "volume": "28.0L"}
        self.assertTrue(equivalent_board_dimensions(retailer, canonical))
        retailer["length"] = "6'0"
        self.assertFalse(equivalent_board_dimensions(retailer, canonical))

    def test_exact_policy_requires_brand_model_and_length(self):
        canonical = {
            "boardSizeId": 10,
            "length": "5'11",
            "width": "18 3/4",
            "thickness": "2 7/16",
            "volume": 28,
            "construction": "CarboTune",
        }
        retailer = {
            "boardSizeId": None,
            "title": "JS Monsta CarboTune 5ft11",
            "length": "5ft11",
            "width": "18.88",
            "thickness": "2.38",
            "volume": "28.0",
            "construction": None,
        }
        self.assertEqual(
            classify_retailer_exact(
                retailer,
                canonical,
                brand_matches=True,
                model_matches=True,
                strong_model_title=True,
            ),
            (True, "equivalent_dimensions"),
        )
        retailer["length"] = "6'0"
        self.assertEqual(
            classify_retailer_exact(
                retailer,
                canonical,
                brand_matches=True,
                model_matches=True,
                strong_model_title=True,
            )[1],
            "length_mismatch",
        )

    def test_missing_dimensions_need_volume_and_strong_title(self):
        canonical = {
            "boardSizeId": 10,
            "length": "5'11",
            "width": "18 3/4",
            "thickness": "2 7/16",
            "volume": 28,
            "construction": "PU",
        }
        retailer = {
            "title": "Lost Rad Ripper PU 5'11 28L",
            "length": "5'11",
            "width": None,
            "thickness": None,
            "volume": 28.2,
            "construction": "PU",
        }
        exact, reason = classify_retailer_exact(
            retailer,
            canonical,
            brand_matches=True,
            model_matches=True,
            strong_model_title=True,
        )
        self.assertTrue(exact)
        self.assertEqual(reason, "length_volume_strong_model")

    def test_reliable_construction_mismatch_is_not_exact(self):
        canonical = {
            "boardSizeId": 10,
            "length": "5'9",
            "width": "19",
            "thickness": "2 7/16",
            "volume": 27.4,
            "construction": "PU",
        }
        retailer = {
            "title": "Sharp Eye #77 C1Carbon 5'9 x 19 x 2.45 x 27.3L",
            "length": "5'9",
            "width": "19",
            "thickness": "2.45",
            "volume": 27.3,
            "construction": "PU",
        }
        self.assertEqual(
            classify_retailer_exact(
                retailer,
                canonical,
                brand_matches=True,
                model_matches=True,
                strong_model_title=True,
            )[1],
            "title_construction_mismatch",
        )

    def test_api_exact_and_close_queries_keep_region_and_brand_guards(self):
        source = inspect.getsource(app.search_inventory)
        self.assertGreaterEqual(source.count("ri.RegionCode = :region_code"), 2)
        self.assertGreaterEqual(source.count("ri.BrandId = :brand_id"), 2)

    def test_eu_linker_uses_title_decimals_but_rejects_ambiguity(self):
        row = {
            "rawProductTitle": "JS Xero Fusion CarboTune 5'9 x 19.62 x 2.44 x 29.9L",
            "lengthFeetInches": "5'9",
            "width": None,
            "thickness": None,
            "volumeLitres": 29.9,
            "construction": None,
        }
        canonical = {
            "boardSizeId": 10,
            "lengthFeetInches": "5'9",
            "width": "19 5/8",
            "thickness": "2 7/16",
            "volumeLitres": 29.9,
            "construction": "CarboTune",
        }
        self.assertEqual(
            select_size_candidate(row, 1, {1: [canonical]})["boardSizeId"],
            10,
        )
        duplicate = {**canonical, "boardSizeId": 11}
        self.assertIsNone(select_size_candidate(row, 1, {1: [canonical, duplicate]}))

    def test_58surf_monsta_carbotune_detail_is_exact(self):
        page_html = """
            <h2 class="product attribute body-sm"><strong class="type">Fabrics</strong><span class="value">Carbotune</span></h2>
            <h2 class="product attribute body-sm"><strong class="type">SKU</strong><span class="value">JS0BO5604SQHTW</span></h2>
            <h2 class="product attribute body-sm"><strong class="type">Features</strong><span class="value">FCS II Thruster</span></h2>
            <h2 class="product attribute body-sm"><strong class="type">Surfboard Volume</strong><span class="value">28.00</span></h2>
            <h2 class="product attribute body-sm"><strong class="type">Surfboard Thickness</strong><span class="value">2.44</span></h2>
            <h2 class="product attribute body-sm"><strong class="type">Surfboard Width</strong><span class="value">18.75</span></h2>
        """
        detail = parse_58surf_product_detail(page_html)
        self.assertEqual(
            detail,
            {
                "sku": "JS0BO5604SQHTW",
                "width": "18.75",
                "thickness": "2.44",
                "volumeLitres": "28.00",
                "construction": "Carbotune",
                "finSetup": "FCS II Thruster",
            },
        )
        normalised = normalise_row({
            "retailerSlug": "58_surf",
            "retailerName": "58 Surf",
            "regionCode": "EU",
            "country": "Portugal",
            "platform": "magento",
            "productTitle": "JS Surfboard 5'11 MONSTA CARBOTUNE Squash Tail - White",
            "productUrl": "https://58surf.com/eng/js-surfboard-5-11-monsta-10-carbotune-squash-tail-white",
            "brand": "JS",
            "priceAmount": "1150.0",
            "priceCurrency": "EUR",
            "isAvailable": True,
            "stockStatus": "in_stock",
            "lengthFeetInches": "5'11",
            **detail,
        })
        self.assertEqual(normalised["width"], "18.75")
        self.assertEqual(normalised["thickness"], "2.44")
        self.assertEqual(normalised["volumeLitres"], "28.00")
        self.assertEqual(normalised["construction"], "Carbotune")
        self.assertEqual(normalised["finSetup"], "FCS II Thruster")

        exact, reason = classify_retailer_exact(
            {
                "boardSizeId": None,
                "title": normalised["rawProductTitle"],
                "length": normalised["lengthFeetInches"],
                "width": normalised["width"],
                "thickness": normalised["thickness"],
                "volume": normalised["volumeLitres"],
                "construction": normalised["construction"],
            },
            {
                "boardSizeId": 179464,
                "length": "5'11",
                "width": "18 3/4",
                "thickness": "2 7/16",
                "volume": 28,
                "construction": "CarboTune",
            },
            brand_matches=True,
            model_matches=True,
            strong_model_title=True,
        )
        self.assertTrue(exact)
        self.assertEqual(reason, "equivalent_dimensions")

    def test_eu_importer_enriches_existing_missing_volume_row(self):
        existing = {
            "retailer_id": 58,
            "product_url": "https://58surf.com/eng/monsta",
            "raw_title": "JS Monsta CarboTune",
            "length": "5'11",
            "volume": None,
        }
        enriched = {**existing, "volume": 28}
        self.assertNotEqual(inventory_key(existing), inventory_key(enriched))
        self.assertEqual(
            inventory_missing_volume_key(existing),
            inventory_missing_volume_key(enriched),
        )
        update_source = inspect.getsource(batch_update_inventory)
        self.assertIn("LengthFeetInches = :length", update_source)
        self.assertIn("Width = :width", update_source)
        self.assertIn("Thickness = :thickness", update_source)
        self.assertIn("VolumeLitres = :volume", update_source)
        self.assertIn("RegionCode = 'EU'", update_source)


if __name__ == "__main__":
    unittest.main()
