import unittest

from scripts.dealers import build_au_coverage_factory_report as report_builder


class AuCoverageFactoryReportTests(unittest.TestCase):
    def test_red_herring_is_classified_as_duplicate_shell(self):
        rows = report_builder.build_candidate_rows()
        row = next(
            candidate for candidate in rows if candidate["dealerName"] == "Red Herring Surf"
        )
        self.assertEqual(row["status"], "duplicate_shell")
        self.assertEqual(row["duplicateOf"], "Board Collective")

    def test_trigger_bros_is_marked_as_running_closeout_retailer(self):
        rows = report_builder.build_candidate_rows()
        row = next(
            candidate for candidate in rows if candidate["dealerName"] == "Trigger Bros Surfboards"
        )
        self.assertEqual(row["status"], "already_running")
        self.assertEqual(row["platform"], "bigcommerce")
        self.assertGreaterEqual(row["priorityScore"], 90)
        self.assertTrue(row["alreadyRunning"])

    def test_manual_review_findings_are_reflected_in_closeout_report(self):
        report = report_builder.build_report()
        self.assertEqual(report["recommendedNextPack"], "None")
        self.assertEqual(report["recommendedNextTarget"], "None")
        self.assertIn("## Parked / Low Priority", report["markdown"])
        self.assertIn("Goodtime Surfboards", report["markdown"])
        self.assertIn("Surf Boardroom", report["markdown"])

    def test_awsm_is_parked_live_not_a_growth_candidate(self):
        rows = report_builder.build_candidate_rows()
        row = next(
            candidate for candidate in rows if candidate["dealerName"] == "AWSM Surf"
        )
        self.assertEqual(row["status"], "parked_live")
        self.assertTrue(row["alreadyRunning"])


if __name__ == "__main__":
    unittest.main()
