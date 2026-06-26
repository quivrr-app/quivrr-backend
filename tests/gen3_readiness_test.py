import unittest
from contextlib import contextmanager
from unittest.mock import patch

from observability import operations_dashboard


@contextmanager
def null_begin():
    yield object()


class Gen3ReadinessTests(unittest.TestCase):
    def test_region_readiness_weights_search_coverage_and_catalogue(self):
        readiness = operations_dashboard._build_region_readiness(
            [
                {
                    "region": "AU",
                    "displayName": "Australia",
                    "retailerStatus": "green",
                    "mfaStatus": "green",
                    "overallStatus": "green",
                    "coverageGapPct": 12.0,
                }
            ],
            {"AU": {"summary": {"availableRows": 42}}},
            {
                "brands": [
                    {
                        "brandName": "Album",
                        "canonicalModelCount": 10,
                        "canonicalSizeCount": 80,
                        "suspiciousModelLossIndicators": [],
                    }
                ]
            },
            {
                "regions": {"AU": {"displayName": "Australia"}},
                "mfaBrands": {"Album": {"AU": "expected"}},
                "retailers": {},
            },
            {
                "regionBreakdown": [
                    {
                        "regionCode": "AU",
                        "supportedRows": 100,
                        "linkedModelPctAfter": 96.0,
                        "linkedSizeFamilyPctAfter": 74.0,
                        "linkedSizePctAfter": 48.0,
                    }
                ]
            },
        )

        self.assertEqual(len(readiness), 1)
        row = readiness[0]
        self.assertEqual(row["region"], "AU")
        self.assertEqual(row["operationalScore"], 100.0)
        self.assertGreater(row["searchScore"], 80.0)
        self.assertEqual(row["coverageScore"], 88.0)
        self.assertEqual(row["catalogueScore"], 100.0)
        self.assertGreater(row["overallScore"], 85.0)

    def test_dashboard_metrics_include_sprint7_payload_sections(self):
        linkage_report = {
            "global": {"supportedRows": 10},
            "regionBreakdown": [
                {
                    "regionCode": "AU",
                    "supportedRows": 10,
                    "linkedModelPctAfter": 90.0,
                    "linkedSizeFamilyPctAfter": 70.0,
                    "linkedSizePctAfter": 40.0,
                }
            ],
            "retailerBreakdown": [],
            "manufacturerBreakdown": [],
            "topRemainingUnmatchedModels": [{"regionCode": "AU", "brandName": "Album", "parsedModel": "proto", "count": 2}],
            "topUnmatchedRetailers": [{"regionCode": "AU", "retailerName": "Legacy AU", "count": 2}],
        }
        canonical_report = {
            "brands": [
                {
                    "brandName": "Album",
                    "canonicalModelCount": 10,
                    "canonicalSizeCount": 80,
                    "suspiciousModelLossIndicators": [],
                }
            ],
            "summary": {"supportedBrandCount": 1, "resolvedBrandCount": 1, "brandsMissingFromSql": []},
        }
        expectations = {
            "regions": {"AU": {"displayName": "Australia"}},
            "mfaBrands": {"Album": {"AU": "expected"}},
            "retailers": {},
        }

        with patch.object(operations_dashboard, "load_source_expectations", return_value=expectations), patch.object(
            operations_dashboard, "_rows", return_value=[]
        ), patch.object(
            operations_dashboard, "_build_supported_linkage_snapshot", return_value=linkage_report
        ), patch.object(
            operations_dashboard, "_build_canonical_completeness_snapshot", return_value=canonical_report
        ), patch.object(
            operations_dashboard, "_build_job_health", return_value=([], {"AU": {"summary": {}, "jobs": []}})
        ), patch.object(
            operations_dashboard.engine, "begin", null_begin
        ):
            payload = operations_dashboard.build_operations_dashboard_metrics()

        self.assertEqual(payload["version"], operations_dashboard.DASHBOARD_VERSION)
        self.assertIn("regionalReadiness", payload)
        self.assertIn("canonicalCompleteness", payload)
        self.assertIn("topUnmatchedModels", payload)
        self.assertIn("topUnmatchedRetailers", payload)
        self.assertIn("readiness", payload["regionDetails"]["AU"])
        self.assertIn("canonicalCompleteness", payload["regionDetails"]["AU"])


if __name__ == "__main__":
    unittest.main()
