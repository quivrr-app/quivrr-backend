import unittest
from unittest.mock import patch

from scripts import run_supported_inventory_linkage_backfill as linkage_backfill
from scripts.run_supported_inventory_linkage_backfill import compute_supported_linkage_report


class SupportedLinkageBackfillTests(unittest.TestCase):
    def test_compute_report_can_scope_to_selected_regions(self):
        report = compute_supported_linkage_report(
            None,
            region_codes=["AU"],
            brands={"album": 1},
            models_by_brand={
                1: [
                    {
                        "boardModelId": 10,
                        "brandId": 1,
                        "modelName": "Bom Dia",
                        "modelKey": "bom dia",
                    }
                ]
            },
            sizes_by_model={},
            inventory_rows=[
                {
                    "inventoryId": 1,
                    "retailerName": "AU Shop",
                    "regionCode": "AU",
                    "brandId": 1,
                    "brandName": "Album",
                    "boardModelId": None,
                    "boardSizeId": None,
                    "rawProductTitle": "Album Bom Dia 5'6",
                    "normalisedProductTitle": "album bom dia 5 6",
                    "lengthFeetInches": "5'6",
                    "width": None,
                    "thickness": None,
                    "volumeLitres": None,
                    "construction": "PU",
                },
                {
                    "inventoryId": 2,
                    "retailerName": "US Shop",
                    "regionCode": "US",
                    "brandId": 1,
                    "brandName": "Album",
                    "boardModelId": None,
                    "boardSizeId": None,
                    "rawProductTitle": "Album Bom Dia 5'6",
                    "normalisedProductTitle": "album bom dia 5 6",
                    "lengthFeetInches": "5'6",
                    "width": None,
                    "thickness": None,
                    "volumeLitres": None,
                    "construction": "PU",
                },
            ],
        )

        self.assertEqual(report["global"]["supportedRows"], 1)
        self.assertEqual([row["regionCode"] for row in report["regionBreakdown"]], ["AU"])

    def test_compute_report_tracks_blockers_and_unmatched_retailers(self):
        report = compute_supported_linkage_report(
            None,
            brands={"album": 1},
            models_by_brand={
                1: [
                    {
                        "boardModelId": 10,
                        "brandId": 1,
                        "modelName": "Bom Dia",
                        "modelKey": "bom dia",
                    }
                ]
            },
            sizes_by_model={
                10: [
                    {
                        "boardSizeId": 501,
                        "lengthFeetInches": "5'6",
                        "width": '19 3/4"',
                        "thickness": '2 1/2"',
                        "volumeLitres": 28.5,
                        "construction": "PU",
                    },
                    {
                        "boardSizeId": 502,
                        "lengthFeetInches": "5'6",
                        "width": '19 3/4"',
                        "thickness": '2 1/2"',
                        "volumeLitres": 28.5,
                        "construction": "PU",
                    },
                ]
            },
            inventory_rows=[
                {
                    "inventoryId": 1,
                    "retailerName": "Legacy AU",
                    "regionCode": "AU",
                    "brandId": 1,
                    "brandName": "Album",
                    "boardModelId": None,
                    "boardSizeId": None,
                    "rawProductTitle": 'Album Bom Dia 5\'6 x 19 3/4" x 2 1/2" 28.5L',
                    "normalisedProductTitle": "album bom dia 5 6 19 3 4 2 1 2 28 5l",
                    "lengthFeetInches": "5'6",
                    "width": '19 3/4"',
                    "thickness": '2 1/2"',
                    "volumeLitres": 28.5,
                    "construction": None,
                },
                {
                    "inventoryId": 2,
                    "retailerName": "Legacy AU",
                    "regionCode": "AU",
                    "brandId": 1,
                    "brandName": "Album",
                    "boardModelId": None,
                    "boardSizeId": None,
                    "rawProductTitle": "Album Unknown Prototype",
                    "normalisedProductTitle": "album unknown prototype",
                    "lengthFeetInches": None,
                    "width": None,
                    "thickness": None,
                    "volumeLitres": None,
                    "construction": None,
                },
            ],
        )

        self.assertEqual(report["global"]["linkedModelRowsAfter"], 1)
        self.assertEqual(report["global"]["missingModelRowsAfter"], 1)
        self.assertEqual(report["global"]["missingConstructionRowsAfter"], 1)
        self.assertEqual(report["global"]["ambiguousBoardSizeRowsAfter"], 1)
        self.assertEqual(report["topUnmatchedRetailers"][0]["retailerName"], "Legacy AU")
        self.assertEqual(report["topUnmatchedRetailers"][0]["count"], 1)

    def test_compute_report_reuses_cached_match_results_for_duplicate_rows(self):
        inventory_rows = [
            {
                "inventoryId": 1,
                "retailerName": "AU Shop",
                "regionCode": "AU",
                "brandId": 1,
                "brandName": "Album",
                "boardModelId": None,
                "boardSizeId": None,
                "rawProductTitle": "Album Bom Dia 5'6",
                "normalisedProductTitle": "album bom dia 5 6",
                "lengthFeetInches": "5'6",
                "width": None,
                "thickness": None,
                "volumeLitres": None,
                "construction": "PU",
            },
            {
                "inventoryId": 2,
                "retailerName": "AU Shop",
                "regionCode": "AU",
                "brandId": 1,
                "brandName": "Album",
                "boardModelId": None,
                "boardSizeId": None,
                "rawProductTitle": "Album Bom Dia 5'6",
                "normalisedProductTitle": "album bom dia 5 6",
                "lengthFeetInches": "5'6",
                "width": None,
                "thickness": None,
                "volumeLitres": None,
                "construction": "PU",
            },
        ]
        model_candidate = {
            "boardModelId": 10,
            "modelName": "Bom Dia",
            "score": 10000,
            "ambiguous": False,
            "candidateCount": 1,
            "ambiguousCandidateCount": 1,
            "candidates": [{"boardModelId": 10, "modelName": "Bom Dia", "score": 10000}],
        }

        with patch.object(linkage_backfill.eu_import, "select_model_candidate", return_value=model_candidate) as select_model, patch.object(
            linkage_backfill.eu_import,
            "select_size_candidate",
            return_value=None,
        ) as select_size, patch.object(
            linkage_backfill,
            "has_size_family_candidate",
            return_value=False,
        ) as size_family:
            report = compute_supported_linkage_report(
                None,
                brands={"album": 1},
                models_by_brand={1: [{"boardModelId": 10, "brandId": 1, "modelName": "Bom Dia", "modelKey": "bom dia"}]},
                sizes_by_model={10: []},
                inventory_rows=inventory_rows,
            )

        self.assertEqual(report["global"]["linkedModelRowsAfter"], 2)
        self.assertEqual(select_model.call_count, 1)
        self.assertEqual(select_size.call_count, 1)
        self.assertEqual(size_family.call_count, 1)


if __name__ == "__main__":
    unittest.main()
