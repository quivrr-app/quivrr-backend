from datetime import datetime, timedelta, timezone
import unittest

from observability.health import _region_health_row, _status_from_freshness, link_quality


class ObservabilityHealthTests(unittest.TestCase):
    def test_freshness_status_calculation(self):
        latest_success = datetime.now(timezone.utc) - timedelta(hours=2)
        status, _reason = _status_from_freshness(
            latest_success,
            36,
            latest_state={"status": "failed", "consecutive_failures": 1},
        )
        self.assertEqual(status, "Warning")

        stale_success = datetime.now(timezone.utc) - timedelta(hours=80)
        status, _reason = _status_from_freshness(stale_success, 36)
        self.assertEqual(status, "High")

    def test_link_quality_calculation(self):
        self.assertEqual(link_quality(80, 100), 0.8)
        self.assertEqual(link_quality(0, 0), 0.0)

    def test_region_health_metric_calculation(self):
        retailer = {
            "inventoryRows": 100,
            "linkedModelRows": 90,
            "linkedSizeRows": 80,
            "retailerCoverage": 5,
            "latestCheckedUtc": datetime.now(timezone.utc),
        }
        manufacturer = {
            "inventoryRows": 50,
            "linkedModelRows": 45,
            "linkedSizeRows": 40,
            "brandCoverage": 6,
            "latestCheckedUtc": datetime.now(timezone.utc),
        }
        row = _region_health_row("EU", retailer, manufacturer)
        self.assertEqual(row["status"], "Healthy")
        self.assertEqual(row["retailerModelLinkRate"], 0.9)
        self.assertEqual(row["manufacturerSizeLinkRate"], 0.8)


if __name__ == "__main__":
    unittest.main()
