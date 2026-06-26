import unittest

from audits.canonical_catalogue_health import summarize_brand_health
from audits.regional_availability_health import summarize_fallback_exclusions
from audits.search_behaviour_matrix import SearchCase, search_case_result


class DataIntegrityAuditTests(unittest.TestCase):
    def test_canonical_audit_detects_dropdown_gap_and_duplicate_normalized_names(self):
        brand_entry = {
            "displayName": "Album",
            "primaryBrandId": 8,
            "brandIds": [8],
        }
        model_rows = [
            {"BoardModelId": 1, "ModelName": "Bom Dia", "ModelTimestamp": None},
            {"BoardModelId": 2, "ModelName": "Bom-Dia", "ModelTimestamp": None},
            {"BoardModelId": 3, "ModelName": "Sunstone", "ModelTimestamp": None},
        ]
        size_rows = [
            {"BoardModelId": 1, "SizeCount": 2, "Construction": "Standard"},
            {"BoardModelId": 3, "SizeCount": 1, "Construction": "Standard"},
        ]
        summary = summarize_brand_health(
            brand_entry,
            model_rows,
            size_rows,
            dropdown_models=["Bom Dia", "Sunstone"],
        )

        self.assertIn("dropdown_model_mismatch", summary["suspiciousModelLossIndicators"])
        self.assertIn("bom dia", summary["duplicateNormalisedModelNames"])
        self.assertIn("Bom-Dia", summary["modelsWithNoSizes"])

    def test_fallback_exclusion_summary_reports_primary_reasons(self):
        summary = summarize_fallback_exclusions(
            [
                {"IsActive": False, "ProductUrl": None, "StockStatus": "sold out", "BoardModelId": None, "BrandId": 8},
                {"IsActive": True, "ProductUrl": "", "StockStatus": "in stock", "BoardModelId": 100, "BrandId": 8},
                {"IsActive": True, "ProductUrl": "https://example.com", "StockStatus": "sold out", "BoardModelId": 100, "BrandId": 8},
                {"IsActive": True, "ProductUrl": "https://example.com", "StockStatus": "available", "BoardModelId": None, "BrandId": 8},
                {"IsActive": True, "ProductUrl": "https://example.com", "StockStatus": "available", "BoardModelId": 100, "BrandId": None},
                {"IsActive": True, "ProductUrl": "https://example.com", "StockStatus": "available", "BoardModelId": 100, "BrandId": 8},
            ]
        )

        self.assertEqual(summary["primaryReasonCounts"]["inactive"], 1)
        self.assertEqual(summary["primaryReasonCounts"]["missing_product_url"], 1)
        self.assertEqual(summary["primaryReasonCounts"]["unsupported_stock_status"], 1)
        self.assertEqual(summary["primaryReasonCounts"]["missing_brand_id"], 1)
        self.assertEqual(summary["primaryReasonCounts"]["eligible"], 2)

    def test_search_case_result_flags_expected_fallback_mismatch(self):
        case = SearchCase(
            region="AU",
            board_size_id=188217,
            brand="Album",
            model="Bom Dia",
            construction="Standard",
            length="5'6",
            label="AU Album Bom Dia smallest",
        )
        payload = {
            "searchVersion": "search_timeout_fix_v2",
            "directManufacturerMatches": [],
            "exactRetailerMatches": [],
            "closeRetailerMatches": [],
            "otherModelMatches": [],
        }
        result = search_case_result(case, payload, fallback_candidate_count=4, close_candidate_count=0)

        self.assertTrue(result["expectedFallback"])
        self.assertFalse(result["actualFallback"])
        self.assertEqual(result["reasonIfMismatch"], "fallback_expected_but_not_returned")


if __name__ == "__main__":
    unittest.main()
