import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.usa import build_us_inventory_quality_report as quality_report
from scripts.usa import import_us_retailer_inventory as us_importer


class UsInventoryQualityReportTests(unittest.TestCase):
    def test_build_quality_report_counts_duplicates_rejects_and_expected_links(self):
        rows = [
            {
                "retailerSlug": "test_shop",
                "retailerName": "Test Shop",
                "regionCode": "US",
                "brandName": "Channel Islands",
                "modelName": "CI Mid",
                "rawProductTitle": "Channel Islands CI Mid 6'6",
                "productUrl": "https://example.com/ci-mid",
                "productImageUrl": "https://example.com/ci-mid.jpg",
                "priceAmount": "999.00",
                "priceCurrency": "USD",
                "stockStatus": "in_stock",
                "lengthFeetInches": "6'6",
                "width": "20 7/8",
                "thickness": "2 7/8",
                "volumeLitres": 42.3,
                "construction": "PU",
                "isAvailable": True,
            },
            {
                "retailerSlug": "test_shop",
                "retailerName": "Test Shop",
                "regionCode": "US",
                "brandName": "Channel Islands",
                "modelName": "CI Mid",
                "rawProductTitle": "Channel Islands CI Mid 6'6",
                "productUrl": "https://example.com/ci-mid",
                "productImageUrl": "https://example.com/ci-mid.jpg",
                "priceAmount": "999.00",
                "priceCurrency": "USD",
                "stockStatus": "in_stock",
                "lengthFeetInches": "6'6",
                "width": "20 7/8",
                "thickness": "2 7/8",
                "volumeLitres": 42.3,
                "construction": "PU",
                "isAvailable": True,
            },
            {
                "retailerSlug": "reject_shop",
                "retailerName": "Reject Shop",
                "regionCode": "US",
                "brandName": "Unknown",
                "modelName": "",
                "rawProductTitle": "Mystery Board",
                "productUrl": "https://example.com/mystery",
                "productImageUrl": "",
                "priceAmount": "",
                "priceCurrency": "USD",
                "stockStatus": "",
                "lengthFeetInches": "",
                "volumeLitres": None,
                "isAvailable": None,
            },
        ]

        report = quality_report.build_quality_report(rows, Path("sample.json"))

        self.assertEqual(report["sourceRows"], 3)
        self.assertEqual(report["totalRows"], 2)
        self.assertEqual(report["duplicateRows"], 1)
        self.assertEqual(report["rejectedRows"], 1)
        self.assertEqual(report["importableRows"], 1)
        self.assertEqual(report["productsWithoutPrices"], 1)
        self.assertEqual(report["productsWithoutImages"], 1)
        self.assertGreaterEqual(report["expectedCanonicalModelLinkedRows"], 1)
        self.assertGreaterEqual(report["expectedBoardSizeLinkedRows"], 0)
        self.assertEqual(report["brandDistribution"][0]["brandName"], "Channel Islands")
        self.assertIn("projectedLinkMetricsBefore", report)
        self.assertIn("projectedLinkMetricsAfter", report)

    def test_main_writes_report_file(self):
        rows = {
            "rows": [
                {
                    "retailerSlug": "test_shop",
                    "retailerName": "Test Shop",
                    "regionCode": "US",
                    "brandName": "Album",
                    "modelName": "Bom Dia",
                    "rawProductTitle": "Album Bom Dia 5'6",
                    "productUrl": "https://example.com/bom-dia",
                    "productImageUrl": "https://example.com/bom-dia.jpg",
                    "priceAmount": "899.00",
                    "priceCurrency": "USD",
                    "stockStatus": "in_stock",
                    "lengthFeetInches": "5'6",
                    "volumeLitres": 26.6,
                    "isAvailable": True,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            output_path = Path(temp_dir) / "report.json"
            input_path.write_text(json.dumps(rows), encoding="utf-8")

            with patch(
                "sys.argv",
                [
                    "build_us_inventory_quality_report.py",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
            ):
                quality_report.main()

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["regionCode"], "US")
            self.assertEqual(payload["importableRows"], 1)

    def test_write_rollback_sql_includes_region_scoped_statements(self):
        rollback_plan = {
            "insertedRetailerIds": [10],
            "insertedInventoryIds": [101, 102],
            "updatedRowsBefore": [
                {
                    "inventoryId": 100,
                    "retailerId": 5,
                    "brandId": 7,
                    "boardModelId": 8,
                    "boardSizeId": 9,
                    "normalisedProductTitle": "Example",
                    "productImageUrl": "https://example.com/image.jpg",
                    "priceAmount": 950,
                    "priceCurrency": "USD",
                    "stockStatus": "in_stock",
                    "construction": "PU",
                    "finSetup": "Thruster",
                    "lengthFeetInches": "6'0",
                    "width": "19 1/4",
                    "thickness": "2 7/16",
                    "volumeLitres": 29.1,
                    "inventoryConfidenceScore": 0.9,
                    "lastCheckedUtc": None,
                    "isActive": 1,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "rollback.sql"
            us_importer.write_rollback_sql(rollback_plan, output_path)
            content = output_path.read_text(encoding="utf-8")

        self.assertIn("RegionCode = 'US'", content)
        self.assertIn("DELETE FROM dbo.RetailerInventory", content)
        self.assertIn("DELETE FROM dbo.Retailers", content)
        self.assertIn("WHERE RegionCode = 'US' AND InventoryId = 100", content)


if __name__ == "__main__":
    unittest.main()
