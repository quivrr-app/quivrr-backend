from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from observability import operations_dashboard as dashboard
from observability.operations_dashboard import (
    STATUS_PRIORITY,
    EXPECTATIONS_PATH,
    MFA_HEALTH_QUERY,
    MFA_REGION_QUERY,
    RETAILER_HEALTH_QUERY,
    RETAILER_REGION_QUERY,
    SUPPORTED_COUNTS_QUERY,
    SUPPORTED_COVERAGE_GAPS_QUERY,
    build_operations_dashboard_metrics,
    classify_search_health,
    classify_source_status,
    combine_status_colors,
    load_source_expectations,
)


class OperationsDashboardMetricsTests(unittest.TestCase):
    def test_expected_source_freshness_statuses(self):
        now = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
        green = classify_source_status(
            "expected",
            now - timedelta(hours=3),
            12,
            now=now,
        )
        yellow = classify_source_status(
            "expected",
            now - timedelta(hours=30),
            12,
            now=now,
        )
        red = classify_source_status(
            "expected",
            now - timedelta(hours=60),
            12,
            now=now,
        )
        self.assertEqual(green.color, "green")
        self.assertEqual(yellow.color, "yellow")
        self.assertEqual(red.color, "red")

    def test_expected_source_zero_rows_is_red(self):
        now = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
        result = classify_source_status(
            "expected",
            now - timedelta(hours=2),
            0,
            now=now,
        )
        self.assertEqual(result.color, "red")
        self.assertEqual(result.label, "zero_rows")

    def test_dealer_network_only_and_not_applicable_are_grey(self):
        dealer_network_only = classify_source_status(
            "dealer_network_only",
            None,
            0,
        )
        not_applicable = classify_source_status(
            "not_applicable",
            None,
            0,
        )
        self.assertEqual(dealer_network_only.color, "grey")
        self.assertEqual(not_applicable.color, "grey")

    def test_planned_sources_are_yellow(self):
        result = classify_source_status(
            "planned",
            None,
            0,
        )
        self.assertEqual(result.color, "yellow")
        self.assertEqual(result.label, "planned")

    def test_search_health_thresholds(self):
        healthy = classify_search_health(80, 55, 30)
        degraded = classify_search_health(65, 35, 18)
        broken = classify_search_health(45, 20, 10)
        partial = classify_search_health(None, None, None)
        self.assertEqual(healthy.color, "green")
        self.assertEqual(degraded.color, "yellow")
        self.assertEqual(broken.color, "red")
        self.assertEqual(partial.color, "yellow")

    def test_combine_status_colors_prefers_highest_severity(self):
        self.assertEqual(combine_status_colors("green", "yellow"), "yellow")
        self.assertEqual(combine_status_colors("grey", "green"), "green")
        self.assertEqual(combine_status_colors("grey", "red", "yellow"), "red")
        self.assertGreater(STATUS_PRIORITY["red"], STATUS_PRIORITY["green"])

    def test_expectations_include_regions_and_special_brand_rules(self):
        expectations = load_source_expectations()
        self.assertIn("AU", expectations["regions"])
        self.assertIn("US", expectations["regions"])
        self.assertIn("Lost", expectations["dealerNetworkOnlyBrands"])
        self.assertIn("Simon Anderson", expectations["australiaOnlyBrands"])
        self.assertEqual(expectations["mfaBrands"]["Lost"]["US"], "dealer_network_only")
        self.assertEqual(expectations["mfaBrands"]["Simon Anderson"]["EU"], "not_applicable")

    def test_build_operations_dashboard_metrics_aggregates_regions_and_gaps(self):
        now = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
        query_results = {
            RETAILER_REGION_QUERY: [
                {
                    "RegionCode": "AU",
                    "ActiveRetailerRows": 100,
                    "AvailableRetailerRows": 75,
                    "LinkedModelRows": 90,
                    "LinkedSizeRows": 60,
                    "RetailerCount": 4,
                    "LatestRetailerRefreshUtc": now - timedelta(hours=2),
                },
                {
                    "RegionCode": "US",
                    "ActiveRetailerRows": 40,
                    "AvailableRetailerRows": 30,
                    "LinkedModelRows": 25,
                    "LinkedSizeRows": 15,
                    "RetailerCount": 2,
                    "LatestRetailerRefreshUtc": now - timedelta(hours=3),
                },
            ],
            MFA_REGION_QUERY: [
                {
                    "RegionCode": "AU",
                    "ActiveMfaRows": 50,
                    "AvailableMfaRows": 25,
                    "LinkedModelRows": 48,
                    "LinkedSizeRows": 45,
                    "BrandCount": 4,
                    "LatestMfaRefreshUtc": now - timedelta(hours=4),
                },
                {
                    "RegionCode": "US",
                    "ActiveMfaRows": 20,
                    "AvailableMfaRows": 10,
                    "LinkedModelRows": 18,
                    "LinkedSizeRows": 16,
                    "BrandCount": 2,
                    "LatestMfaRefreshUtc": now - timedelta(hours=6),
                },
            ],
            RETAILER_HEALTH_QUERY: [
                {
                    "RegionCode": "AU",
                    "RetailerName": "Aloha Surf Manly",
                    "ActiveRows": 100,
                    "AvailableRows": 75,
                    "LinkedModelRows": 90,
                    "LinkedSizeRows": 60,
                    "LatestRefreshUtc": now - timedelta(hours=2),
                },
                {
                    "RegionCode": "US",
                    "RetailerName": "Surf Station",
                    "ActiveRows": 40,
                    "AvailableRows": 30,
                    "LinkedModelRows": 25,
                    "LinkedSizeRows": 15,
                    "LatestRefreshUtc": now - timedelta(hours=3),
                },
            ],
            MFA_HEALTH_QUERY: [
                {
                    "RegionCode": "AU",
                    "BrandName": "JS Industries",
                    "ActiveRows": 50,
                    "AvailableRows": 25,
                    "LinkedModelRows": 48,
                    "LinkedSizeRows": 45,
                    "LatestRefreshUtc": now - timedelta(hours=4),
                },
                {
                    "RegionCode": "US",
                    "BrandName": "JS Industries",
                    "ActiveRows": 20,
                    "AvailableRows": 10,
                    "LinkedModelRows": 18,
                    "LinkedSizeRows": 16,
                    "LatestRefreshUtc": now - timedelta(hours=6),
                },
            ],
            SUPPORTED_COUNTS_QUERY: [
                {
                    "RegionCode": "AU",
                    "SupportedRows": 90,
                    "UnsupportedRows": 10,
                    "UsedSupportedRows": 5,
                },
                {
                    "RegionCode": "US",
                    "SupportedRows": 35,
                    "UnsupportedRows": 5,
                    "UsedSupportedRows": 2,
                },
            ],
            SUPPORTED_COVERAGE_GAPS_QUERY: [
                {
                    "RegionCode": "AU",
                    "SupportedModelCount": 2,
                    "RetailerModelCount": 1,
                    "MfaModelCount": 1,
                    "StockedAnywhereModelCount": 1,
                },
                {
                    "RegionCode": "US",
                    "SupportedModelCount": 2,
                    "RetailerModelCount": 1,
                    "MfaModelCount": 1,
                    "StockedAnywhereModelCount": 2,
                },
            ],
        }

        class FakeContext:
            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, tb):
                return False

        linkage_report = {
            "regionBreakdown": [
                {
                    "regionCode": "AU",
                    "linkedModelPctAfter": 90.0,
                    "linkedSizeFamilyPctAfter": 55.0,
                    "linkedSizePctAfter": 30.0,
                },
                {
                    "regionCode": "US",
                    "linkedModelPctAfter": 70.0,
                    "linkedSizeFamilyPctAfter": 40.0,
                    "linkedSizePctAfter": 20.0,
                },
            ],
            "retailerBreakdown": [
                {
                    "regionCode": "AU",
                    "name": "Aloha Surf Manly",
                    "linkedModelPctAfter": 90.0,
                    "linkedSizeFamilyPctAfter": 55.0,
                    "linkedSizePctAfter": 30.0,
                },
                {
                    "regionCode": "US",
                    "name": "Surf Station",
                    "linkedModelPctAfter": 62.5,
                    "linkedSizeFamilyPctAfter": 37.5,
                    "linkedSizePctAfter": 20.0,
                },
            ],
            "manufacturerBreakdown": [
                {
                    "regionCode": "AU",
                    "name": "JS Industries",
                    "linkedModelPctAfter": 96.0,
                    "linkedSizeFamilyPctAfter": 90.0,
                    "linkedSizePctAfter": 90.0,
                },
                {
                    "regionCode": "US",
                    "name": "JS Industries",
                    "linkedModelPctAfter": 90.0,
                    "linkedSizeFamilyPctAfter": 80.0,
                    "linkedSizePctAfter": 80.0,
                },
            ],
        }

        def fake_rows(query: str, params=None):
            return query_results[query]

        with patch.object(dashboard, "_rows", side_effect=fake_rows), patch.object(
            dashboard.engine, "begin", return_value=FakeContext()
        ):
            metrics = build_operations_dashboard_metrics(
                now=now,
                expectations_path=EXPECTATIONS_PATH,
                linkage_report_builder=lambda _conn: linkage_report,
            )

        self.assertEqual(metrics["regions"][:2], ["AU", "EU"])
        self.assertEqual(metrics["version"], dashboard.DASHBOARD_VERSION)
        self.assertEqual(metrics["regionOverview"][0]["region"], "AU")
        self.assertEqual(metrics["regionOverview"][0]["statusColor"], "green")
        self.assertEqual(metrics["inventoryCounts"][0]["activeRetailerInventoryRows"], 100)
        self.assertEqual(metrics["inventoryCounts"][0]["newSupportedBoards"], 85)
        self.assertIn("alerts", metrics)
        au_gaps = next(item for item in metrics["coverageGaps"] if item["region"] == "AU")
        us_gaps = next(item for item in metrics["coverageGaps"] if item["region"] == "US")
        self.assertEqual(au_gaps["supportedCanonicalModelsNoStockAnywhere"]["count"], 1)
        self.assertEqual(au_gaps["modelsAvailableOnlyViaMfa"]["count"], 0)
        self.assertEqual(us_gaps["modelsAvailableOnlyViaRetailers"]["count"], 1)
        self.assertEqual(us_gaps["supportedCanonicalModelsNoStockAnywhere"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
