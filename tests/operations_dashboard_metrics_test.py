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
        healthy = classify_search_health(86, 61, 30)
        degraded = classify_search_health(80, 45, 18)
        broken = classify_search_health(74.9, 39.9, 10)
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
            dashboard.SUPPORTED_MODEL_TOTAL_QUERY: [
                {
                    "SupportedModelCount": 2,
                },
            ],
            dashboard.SUPPORTED_MFA_MODEL_IDS_QUERY: [
                {
                    "RegionCode": "AU",
                    "BoardModelId": 1,
                },
                {
                    "RegionCode": "US",
                    "BoardModelId": 2,
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
                    "projectedRetailerModelIds": [1, 2],
                },
                {
                    "regionCode": "US",
                    "linkedModelPctAfter": 70.0,
                    "linkedSizeFamilyPctAfter": 40.0,
                    "linkedSizePctAfter": 20.0,
                    "projectedRetailerModelIds": [1],
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
            "regionCoverage": [
                {"regionCode": "AU", "projectedRetailerModelIds": [1, 2]},
                {"regionCode": "US", "projectedRetailerModelIds": [1]},
            ],
        }

        def fake_rows(query: str, params=None):
            return query_results[query]

        with patch.object(dashboard, "_rows", side_effect=fake_rows), patch.object(
            dashboard.engine, "begin", return_value=FakeContext()
        ), patch.object(
            dashboard,
            "_catalogue_metrics",
            return_value={"latestSuccessUtc": "2026-06-20T00:00:00Z", "modelCount": 500},
        ), patch.object(
            dashboard,
            "_load_job_state",
            return_value=None,
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
        self.assertIn("retailerHealthByRegion", metrics)
        self.assertIn("jobHealth", metrics)
        self.assertIn("jobHealthByRegion", metrics)
        self.assertIn("jobContracts", metrics)
        self.assertIn("jobContractsByRegion", metrics)
        self.assertIn("regionDetails", metrics)
        au_gaps = next(item for item in metrics["coverageGaps"] if item["region"] == "AU")
        us_gaps = next(item for item in metrics["coverageGaps"] if item["region"] == "US")
        self.assertEqual(au_gaps["supportedCanonicalModelsNoStockAnywhere"]["count"], 0)
        self.assertEqual(au_gaps["modelsAvailableOnlyViaMfa"]["count"], 0)
        self.assertEqual(us_gaps["modelsAvailableOnlyViaRetailers"]["count"], 1)
        self.assertEqual(us_gaps["supportedCanonicalModelsNoStockAnywhere"]["count"], 0)
        self.assertEqual(metrics["retailerHealthByRegion"]["AU"]["summary"]["healthyRetailers"], 1)
        self.assertEqual(metrics["retailerHealthByRegion"]["US"]["summary"]["configuredRetailers"], 20)
        self.assertGreater(metrics["jobHealthByRegion"]["AU"]["summary"]["configuredJobs"], 0)
        self.assertIn("summary", metrics["alertSummary"])
        self.assertIn("topAlerts", metrics["alertSummary"])
        self.assertEqual(metrics["regionDetails"]["AU"]["retailerHealth"]["summary"]["activeRows"], 100)
        self.assertEqual(metrics["regionDetails"]["AU"]["retailerHealth"]["summary"]["configuredRetailers"], 4)
        self.assertIn("jobHealth", metrics["regionDetails"]["AU"])
        self.assertIn("jobContracts", metrics["regionDetails"]["AU"])

    def test_region_level_stale_alert_suppresses_per_retailer_spam(self):
        now = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
        query_results = {
            RETAILER_REGION_QUERY: [
                {
                    "RegionCode": "AU",
                    "ActiveRetailerRows": 100,
                    "AvailableRetailerRows": 75,
                    "LinkedModelRows": 90,
                    "LinkedSizeRows": 60,
                    "RetailerCount": 2,
                    "LatestRetailerRefreshUtc": now - timedelta(hours=72),
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
                    "LatestMfaRefreshUtc": now - timedelta(hours=2),
                },
            ],
            RETAILER_HEALTH_QUERY: [
                {
                    "RegionCode": "AU",
                    "RetailerName": "Aloha Surf Manly",
                    "ActiveRows": 60,
                    "AvailableRows": 45,
                    "LinkedModelRows": 50,
                    "LinkedSizeRows": 30,
                    "LatestRefreshUtc": now - timedelta(hours=72),
                },
                {
                    "RegionCode": "AU",
                    "RetailerName": "Another AU Retailer",
                    "ActiveRows": 40,
                    "AvailableRows": 30,
                    "LinkedModelRows": 35,
                    "LinkedSizeRows": 20,
                    "LatestRefreshUtc": now - timedelta(hours=72),
                },
            ],
            MFA_HEALTH_QUERY: [],
            SUPPORTED_COUNTS_QUERY: [
                {
                    "RegionCode": "AU",
                    "SupportedRows": 90,
                    "UnsupportedRows": 10,
                    "UsedSupportedRows": 5,
                },
            ],
            dashboard.SUPPORTED_MODEL_TOTAL_QUERY: [
                {
                    "SupportedModelCount": 10,
                },
            ],
            dashboard.SUPPORTED_MFA_MODEL_IDS_QUERY: [
                {"RegionCode": "AU", "BoardModelId": 1},
                {"RegionCode": "AU", "BoardModelId": 2},
                {"RegionCode": "AU", "BoardModelId": 3},
                {"RegionCode": "AU", "BoardModelId": 4},
                {"RegionCode": "AU", "BoardModelId": 5},
                {"RegionCode": "AU", "BoardModelId": 6},
                {"RegionCode": "AU", "BoardModelId": 7},
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
                    "projectedRetailerModelIds": [1, 2, 3, 4, 5, 6, 7, 8],
                }
            ],
            "retailerBreakdown": [
                {
                    "regionCode": "AU",
                    "name": "Aloha Surf Manly",
                    "linkedModelPctAfter": 80.0,
                    "linkedSizeFamilyPctAfter": 45.0,
                    "linkedSizePctAfter": 20.0,
                },
                {
                    "regionCode": "AU",
                    "name": "Another AU Retailer",
                    "linkedModelPctAfter": 75.0,
                    "linkedSizeFamilyPctAfter": 40.0,
                    "linkedSizePctAfter": 15.0,
                },
            ],
            "manufacturerBreakdown": [],
            "regionCoverage": [
                {"regionCode": "AU", "projectedRetailerModelIds": [1, 2, 3, 4, 5, 6, 7, 8]},
            ],
        }

        def fake_rows(query: str, params=None):
            return query_results[query]

        with patch.object(dashboard, "_rows", side_effect=fake_rows), patch.object(
            dashboard.engine, "begin", return_value=FakeContext()
        ), patch.object(
            dashboard,
            "_catalogue_metrics",
            return_value={"latestSuccessUtc": "2026-06-25T00:00:00Z", "modelCount": 500},
        ), patch.object(
            dashboard,
            "_load_job_state",
            return_value=None,
        ):
            metrics = build_operations_dashboard_metrics(
                now=now,
                expectations_path=EXPECTATIONS_PATH,
                linkage_report_builder=lambda _conn: linkage_report,
            )

        alerts = metrics["alerts"]
        self.assertTrue(any(alert["category"] == "retailer_inventory" for alert in alerts))
        self.assertFalse(any(alert["category"] == "retailer_source" for alert in alerts))

    def test_job_health_uses_job_state_failures_when_present(self):
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
                    "LatestRetailerRefreshUtc": now - timedelta(hours=80),
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
                    "LatestMfaRefreshUtc": now - timedelta(hours=96),
                },
            ],
            RETAILER_HEALTH_QUERY: [],
            MFA_HEALTH_QUERY: [],
            SUPPORTED_COUNTS_QUERY: [],
            dashboard.SUPPORTED_MODEL_TOTAL_QUERY: [{"SupportedModelCount": 0}],
            dashboard.SUPPORTED_MFA_MODEL_IDS_QUERY: [],
        }

        class FakeContext:
            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_rows(query: str, params=None):
            return query_results[query]

        def fake_job_state(name: str):
            if name == "inventory_au":
                return {
                    "status": "failed",
                    "latest_status_timestamp_utc": "2026-06-25T16:30:25Z",
                    "latest_success_timestamp_utc": "2026-06-22T16:30:00Z",
                    "duration_seconds": 31.4,
                }
            if name == "mfa_au":
                return {
                    "status": "failed",
                    "latest_status_timestamp_utc": "2026-06-25T17:00:28Z",
                    "latest_success_timestamp_utc": "2026-06-22T17:00:00Z",
                    "duration_seconds": 28.1,
                }
            return None

        with patch.object(dashboard, "_rows", side_effect=fake_rows), patch.object(
            dashboard.engine, "begin", return_value=FakeContext()
        ), patch.object(
            dashboard,
            "_catalogue_metrics",
            return_value={"latestSuccessUtc": "2026-06-24T03:00:00Z", "modelCount": 500},
        ), patch.object(
            dashboard,
            "_load_job_state",
            side_effect=fake_job_state,
        ):
            metrics = build_operations_dashboard_metrics(
                now=now,
                expectations_path=EXPECTATIONS_PATH,
                linkage_report_builder=lambda _conn: {
                    "regionBreakdown": [],
                    "retailerBreakdown": [],
                    "manufacturerBreakdown": [],
                    "global": {},
                    "supportedBrands": [],
                    "regionCoverage": [],
                },
            )

        au_jobs = metrics["jobHealthByRegion"]["AU"]["jobs"]
        inventory_job = next(row for row in au_jobs if row["jobName"] == "quivrr-nightly-au-inventory")
        mfa_job = next(row for row in au_jobs if row["jobName"] == "quivrr-mfr-availability")
        self.assertEqual(inventory_job["status"], "red")
        self.assertEqual(inventory_job["statusLabel"], "failed")
        self.assertEqual(inventory_job["lastFailedUtc"], "2026-06-25T16:30:25Z")
        self.assertEqual(mfa_job["status"], "red")
        self.assertTrue(any(alert["category"] == "job_health" for alert in metrics["alerts"]))

    def test_legacy_region_uses_live_retailer_count_when_expectations_missing(self):
        now = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
        query_results = {
            RETAILER_REGION_QUERY: [
                {
                    "RegionCode": "AU",
                    "ActiveRetailerRows": 50,
                    "AvailableRetailerRows": 45,
                    "LinkedModelRows": 0,
                    "LinkedSizeRows": 0,
                    "RetailerCount": 3,
                    "LatestRetailerRefreshUtc": now - timedelta(hours=1),
                },
            ],
            MFA_REGION_QUERY: [],
            RETAILER_HEALTH_QUERY: [
                {
                    "RegionCode": "AU",
                    "RetailerName": "Legacy One",
                    "ActiveRows": 20,
                    "AvailableRows": 20,
                    "LinkedModelRows": 0,
                    "LinkedSizeRows": 0,
                    "LatestRefreshUtc": now - timedelta(hours=1),
                },
                {
                    "RegionCode": "AU",
                    "RetailerName": "Legacy Two",
                    "ActiveRows": 15,
                    "AvailableRows": 15,
                    "LinkedModelRows": 0,
                    "LinkedSizeRows": 0,
                    "LatestRefreshUtc": now - timedelta(hours=1),
                },
                {
                    "RegionCode": "AU",
                    "RetailerName": "Legacy Three",
                    "ActiveRows": 15,
                    "AvailableRows": 10,
                    "LinkedModelRows": 0,
                    "LinkedSizeRows": 0,
                    "LatestRefreshUtc": now - timedelta(hours=1),
                },
            ],
            MFA_HEALTH_QUERY: [],
            SUPPORTED_COUNTS_QUERY: [
                {"RegionCode": "AU", "SupportedRows": 50, "UnsupportedRows": 0, "UsedSupportedRows": 0},
            ],
            dashboard.SUPPORTED_MODEL_TOTAL_QUERY: [{"SupportedModelCount": 10}],
            dashboard.SUPPORTED_MFA_MODEL_IDS_QUERY: [],
        }

        class FakeContext:
            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch.object(dashboard, "_rows", side_effect=lambda query, params=None: query_results[query]), patch.object(
            dashboard.engine, "begin", return_value=FakeContext()
        ), patch.object(
            dashboard,
            "_catalogue_metrics",
            return_value={"latestSuccessUtc": "2026-06-25T00:00:00Z", "modelCount": 500},
        ), patch.object(
            dashboard,
            "_load_job_state",
            return_value=None,
        ):
            metrics = build_operations_dashboard_metrics(
                now=now,
                expectations_path=EXPECTATIONS_PATH,
                linkage_report_builder=lambda _conn: {
                    "regionBreakdown": [
                        {
                            "regionCode": "AU",
                            "linkedModelPctAfter": 76.66,
                            "linkedSizeFamilyPctAfter": 46.41,
                            "linkedSizePctAfter": 23.13,
                            "projectedRetailerModelIds": [1, 2, 3, 4, 5, 6],
                        }
                    ],
                    "retailerBreakdown": [
                        {"regionCode": "AU", "name": "Legacy One", "linkedModelPctAfter": 80.0, "linkedSizeFamilyPctAfter": 50.0, "linkedSizePctAfter": 30.0},
                        {"regionCode": "AU", "name": "Legacy Two", "linkedModelPctAfter": 70.0, "linkedSizeFamilyPctAfter": 40.0, "linkedSizePctAfter": 20.0},
                        {"regionCode": "AU", "name": "Legacy Three", "linkedModelPctAfter": 60.0, "linkedSizeFamilyPctAfter": 30.0, "linkedSizePctAfter": 10.0},
                    ],
                    "manufacturerBreakdown": [],
                    "global": {},
                    "supportedBrands": [],
                    "regionCoverage": [{"regionCode": "AU", "projectedRetailerModelIds": [1, 2, 3, 4, 5, 6]}],
                },
            )

        summary = metrics["retailerHealthByRegion"]["AU"]["summary"]
        self.assertEqual(summary["configuredRetailers"], 3)
        self.assertEqual(metrics["regionDetails"]["AU"]["searchQuality"]["supportedModelLinkagePct"], 76.66)

    def test_quality_alerts_include_metric_context(self):
        now = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
        query_results = {
            RETAILER_REGION_QUERY: [
                {
                    "RegionCode": "EU",
                    "ActiveRetailerRows": 100,
                    "AvailableRetailerRows": 80,
                    "LinkedModelRows": 0,
                    "LinkedSizeRows": 0,
                    "RetailerCount": 2,
                    "LatestRetailerRefreshUtc": now - timedelta(hours=2),
                },
            ],
            MFA_REGION_QUERY: [
                {
                    "RegionCode": "EU",
                    "ActiveMfaRows": 20,
                    "AvailableMfaRows": 20,
                    "LinkedModelRows": 20,
                    "LinkedSizeRows": 10,
                    "BrandCount": 1,
                    "LatestMfaRefreshUtc": now - timedelta(hours=2),
                }
            ],
            RETAILER_HEALTH_QUERY: [],
            MFA_HEALTH_QUERY: [],
            SUPPORTED_COUNTS_QUERY: [{"RegionCode": "EU", "SupportedRows": 100, "UnsupportedRows": 0, "UsedSupportedRows": 0}],
            dashboard.SUPPORTED_MODEL_TOTAL_QUERY: [{"SupportedModelCount": 10}],
            dashboard.SUPPORTED_MFA_MODEL_IDS_QUERY: [{"RegionCode": "EU", "BoardModelId": 1}],
        }

        class FakeContext:
            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch.object(dashboard, "_rows", side_effect=lambda query, params=None: query_results[query]), patch.object(
            dashboard.engine, "begin", return_value=FakeContext()
        ), patch.object(
            dashboard,
            "_catalogue_metrics",
            return_value={"latestSuccessUtc": "2026-06-25T00:00:00Z", "modelCount": 500},
        ), patch.object(
            dashboard,
            "_load_job_state",
            return_value=None,
        ):
            metrics = build_operations_dashboard_metrics(
                now=now,
                expectations_path=EXPECTATIONS_PATH,
                linkage_report_builder=lambda _conn: {
                    "regionBreakdown": [
                        {
                            "regionCode": "EU",
                            "linkedModelPctAfter": 76.96,
                            "linkedSizeFamilyPctAfter": 58.3,
                            "linkedSizePctAfter": 32.71,
                            "projectedRetailerModelIds": [1, 2, 3, 4, 5, 6, 7],
                        }
                    ],
                    "retailerBreakdown": [],
                    "manufacturerBreakdown": [],
                    "global": {},
                    "supportedBrands": [],
                    "regionCoverage": [{"regionCode": "EU", "projectedRetailerModelIds": [1, 2, 3, 4, 5, 6, 7]}],
                },
            )

        alerts = metrics["alertSummary"]["allAlerts"]
        search_alert = next(alert for alert in alerts if alert["category"] == "search_quality" and alert["region"] == "EU")
        coverage_alert = next(alert for alert in alerts if alert["category"] == "market_coverage" and alert["region"] == "EU")
        self.assertEqual(search_alert["metricName"], "modelLinkPct")
        self.assertEqual(search_alert["currentValue"], 76.96)
        self.assertEqual(search_alert["threshold"], 85.0)
        self.assertTrue(search_alert["suggestedAction"])
        self.assertEqual(coverage_alert["metricName"], "noStockAnywherePct")
        self.assertEqual(coverage_alert["threshold"], 20.0)
        self.assertEqual(coverage_alert["title"], "EU market coverage limited")
        self.assertIn("3 of 10 supported canonical models", coverage_alert["message"])
        overview = next(row for row in metrics["regionOverview"] if row["region"] == "EU")
        self.assertEqual(overview["dataQualityStatus"], "yellow")
        self.assertEqual(overview["coverageQualityStatus"], "yellow")

    def test_job_state_only_jobs_without_local_state_are_informational_grey(self):
        now = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
        query_results = {
            RETAILER_REGION_QUERY: [
                {
                    "RegionCode": "AU",
                    "ActiveRetailerRows": 100,
                    "AvailableRetailerRows": 80,
                    "LinkedModelRows": 70,
                    "LinkedSizeRows": 40,
                    "RetailerCount": 2,
                    "LatestRetailerRefreshUtc": now - timedelta(hours=2),
                },
            ],
            MFA_REGION_QUERY: [
                {
                    "RegionCode": "AU",
                    "ActiveMfaRows": 20,
                    "AvailableMfaRows": 20,
                    "LinkedModelRows": 15,
                    "LinkedSizeRows": 10,
                    "BrandCount": 1,
                    "LatestMfaRefreshUtc": now - timedelta(hours=2),
                }
            ],
            RETAILER_HEALTH_QUERY: [],
            MFA_HEALTH_QUERY: [],
            SUPPORTED_COUNTS_QUERY: [{"RegionCode": "AU", "SupportedRows": 100, "UnsupportedRows": 0, "UsedSupportedRows": 0}],
            dashboard.SUPPORTED_MODEL_TOTAL_QUERY: [{"SupportedModelCount": 10}],
            dashboard.SUPPORTED_MFA_MODEL_IDS_QUERY: [{"RegionCode": "AU", "BoardModelId": 1}],
        }

        class FakeContext:
            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch.object(dashboard, "_rows", side_effect=lambda query, params=None: query_results[query]), patch.object(
            dashboard.engine, "begin", return_value=FakeContext()
        ), patch.object(
            dashboard,
            "_catalogue_metrics",
            return_value={"latestSuccessUtc": "2026-06-25T00:00:00Z", "modelCount": 500},
        ), patch.object(
            dashboard,
            "_load_job_state",
            return_value=None,
        ):
            metrics = build_operations_dashboard_metrics(
                now=now,
                expectations_path=EXPECTATIONS_PATH,
                linkage_report_builder=lambda _conn: {
                    "regionBreakdown": [
                        {
                            "regionCode": "AU",
                            "linkedModelPctAfter": 80.0,
                            "linkedSizeFamilyPctAfter": 50.0,
                            "linkedSizePctAfter": 20.0,
                            "projectedRetailerModelIds": [1, 2, 3],
                        }
                    ],
                    "retailerBreakdown": [],
                    "manufacturerBreakdown": [],
                    "global": {},
                    "supportedBrands": [],
                    "regionCoverage": [{"regionCode": "AU", "projectedRetailerModelIds": [1, 2, 3]}],
                },
            )

        market_job = next(
            row for row in metrics["jobHealthByRegion"]["AU"]["jobs"]
            if row["jobName"] == "quivrr-market-intelligence"
        )
        self.assertEqual(market_job["status"], "grey")
        self.assertEqual(market_job["statusLabel"], "telemetry_pending")


if __name__ == "__main__":
    unittest.main()
