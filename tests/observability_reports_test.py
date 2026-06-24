import unittest

from observability.reports import build_daily_report_html, build_weekly_report_html


SAMPLE_SNAPSHOT = {
    "generatedAtUtc": "2026-06-24T00:00:00Z",
    "platformHealth": {"status": "Healthy", "reason": "All monitored services are inside their freshness windows."},
    "regionHealth": [
        {
            "region": "AU",
            "status": "Healthy",
            "inventoryStatus": "Healthy",
            "mfaStatus": "Healthy",
            "retailerInventoryRows": 100,
            "manufacturerInventoryRows": 40,
            "retailerModelLinkRate": 0.9,
            "retailerSizeLinkRate": 0.85,
            "manufacturerModelLinkRate": 0.88,
            "manufacturerSizeLinkRate": 0.82,
            "retailerCoverage": 10,
            "brandCoverage": 8,
        }
    ],
    "catalogueHealth": {"status": "Healthy", "reason": "Fresh.", "modelCount": 513, "sizeCount": 3200},
    "inventoryHealth": {"nullRegionCounts": {"retailerInventoryNullRegionRows": 0, "manufacturerInventoryNullRegionRows": 0}, "regionLeakage": {"retailerRegionLeakageRows": 0}},
    "mfaHealth": {},
    "bodhiHealth": {"status": "Healthy", "reason": "Board Guide API healthy."},
    "openIssues": [],
    "recommendedActions": ["No urgent intervention required; continue monitoring scheduled runs."],
}


class ObservabilityReportsTests(unittest.TestCase):
    def test_daily_report_html_rendering(self):
        html = build_daily_report_html(SAMPLE_SNAPSHOT)
        self.assertIn("Quivrr Daily Observability Report", html)
        self.assertIn("Platform Health", html)
        self.assertIn("Region Health", html)

    def test_weekly_report_html_rendering(self):
        html = build_weekly_report_html(SAMPLE_SNAPSHOT)
        self.assertIn("Quivrr Weekly Platform Report", html)
        self.assertIn("Executive Summary", html)
        self.assertIn("Retailer Coverage Gaps", html)


if __name__ == "__main__":
    unittest.main()
