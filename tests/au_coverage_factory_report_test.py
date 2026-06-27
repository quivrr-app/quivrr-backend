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

    def test_trigger_bros_is_recommended_bigcommerce_candidate(self):
        rows = report_builder.build_candidate_rows()
        row = next(
            candidate for candidate in rows if candidate["dealerName"] == "Trigger Bros Surfboards"
        )
        self.assertEqual(row["status"], "ready_bigcommerce")
        self.assertEqual(row["platform"], "bigcommerce")
        self.assertGreaterEqual(row["priorityScore"], 90)

    def test_pack_grouping_keeps_bigcommerce_pack_visible(self):
        report = report_builder.build_report()
        self.assertEqual(report["recommendedNextPack"], "BigCommerce Pack")
        self.assertIn("`ready_bigcommerce`", report["markdown"])
        self.assertIn("Trigger Bros Surfboards", report["markdown"])


if __name__ == "__main__":
    unittest.main()
