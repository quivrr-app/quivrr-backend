import unittest

from observability.inventory_link_health import (
    build_retailer_payload,
    build_snapshot_payload,
    collect_inventory_link_health,
    link_pct,
)


class InventoryLinkHealthReportTests(unittest.TestCase):
    def test_link_pct_is_zero_safe_and_percentage_based(self):
        self.assertEqual(link_pct(0, 0), 0.0)
        self.assertEqual(link_pct(4602, 9211), 49.96)
        self.assertEqual(link_pct(1973, 9211), 21.42)

    def test_snapshot_payload_shape_and_canonical_size_link_alias_fields(self):
        payload = build_snapshot_payload(
            region="EU",
            total_rows=9211,
            linked_model_rows=4602,
            linked_size_rows=1973,
            retailer_count=18,
            generated_at_utc="2026-06-24T00:00:00Z",
        )
        self.assertEqual(
            set(payload.keys()),
            {
                "event",
                "service",
                "generated_at_utc",
                "region",
                "total_rows",
                "linked_model_rows",
                "linked_size_rows",
                "linked_model_pct",
                "linked_size_pct",
                "canonical_size_linked_rows",
                "canonical_size_linked_pct",
                "searchable_rows",
                "searchable_pct",
                "retailer_count",
            },
        )
        self.assertEqual(payload["event"], "inventory_link_health_snapshot")
        self.assertEqual(payload["service"], "inventory_link_health")
        self.assertEqual(payload["region"], "EU")
        self.assertEqual(payload["canonical_size_linked_rows"], 1973)
        self.assertEqual(payload["canonical_size_linked_pct"], 21.42)
        self.assertEqual(payload["searchable_rows"], 1973)
        self.assertEqual(payload["searchable_pct"], 21.42)
        self.assertEqual(payload["linked_model_pct"], 49.96)
        self.assertEqual(payload["searchable_rows"], payload["canonical_size_linked_rows"])
        self.assertEqual(payload["searchable_pct"], payload["canonical_size_linked_pct"])

    def test_retailer_payload_shape_and_canonical_size_link_alias_fields(self):
        payload = build_retailer_payload(
            region="EU",
            retailer_name="Example Surf Shop",
            total_rows=100,
            linked_model_rows=80,
            linked_size_rows=25,
            generated_at_utc="2026-06-24T00:00:00Z",
        )
        self.assertEqual(
            set(payload.keys()),
            {
                "event",
                "service",
                "generated_at_utc",
                "region",
                "retailer_name",
                "total_rows",
                "linked_model_rows",
                "linked_size_rows",
                "linked_model_pct",
                "linked_size_pct",
                "canonical_size_linked_rows",
                "canonical_size_linked_pct",
                "searchable_rows",
                "searchable_pct",
            },
        )
        self.assertEqual(payload["event"], "inventory_link_health_retailer")
        self.assertEqual(payload["canonical_size_linked_rows"], 25)
        self.assertEqual(payload["canonical_size_linked_pct"], 25.0)
        self.assertEqual(payload["searchable_rows"], 25)
        self.assertEqual(payload["searchable_pct"], 25.0)
        self.assertEqual(payload["searchable_rows"], payload["canonical_size_linked_rows"])
        self.assertEqual(payload["searchable_pct"], payload["canonical_size_linked_pct"])

    def test_queries_filter_active_rows_only(self):
        from observability.inventory_link_health import RETAILER_QUERY, SNAPSHOT_QUERY

        self.assertIn("WHERE ri.IsActive = 1", SNAPSHOT_QUERY)
        self.assertIn("WHERE ri.IsActive = 1", RETAILER_QUERY)
        self.assertNotIn("COALESCE(ri.IsActive, 1) = 1", SNAPSHOT_QUERY)
        self.assertNotIn("COALESCE(ri.IsActive, 1) = 1", RETAILER_QUERY)

    def test_collect_inventory_link_health_sorts_regions_and_retailers(self):
        snapshot_rows = [
            {"RegionCode": "ID", "TotalRows": 50, "LinkedModelRows": 20, "LinkedSizeRows": 10, "RetailerCount": 2},
            {"RegionCode": "AU", "TotalRows": 60, "LinkedModelRows": 30, "LinkedSizeRows": 18, "RetailerCount": 3},
            {"RegionCode": "EU", "TotalRows": 70, "LinkedModelRows": 40, "LinkedSizeRows": 21, "RetailerCount": 4},
        ]
        retailer_rows = [
            {"RegionCode": "AU", "RetailerName": "Zulu", "TotalRows": 10, "LinkedModelRows": 8, "LinkedSizeRows": 4},
            {"RegionCode": "EU", "RetailerName": "Alpha", "TotalRows": 20, "LinkedModelRows": 10, "LinkedSizeRows": 6},
            {"RegionCode": "ID", "RetailerName": "Beta", "TotalRows": 15, "LinkedModelRows": 7, "LinkedSizeRows": 5},
        ]

        from observability import inventory_link_health as report

        original_rows = report._rows
        try:
            calls = []

            def fake_rows(query):
                calls.append(query)
                return snapshot_rows if len(calls) == 1 else retailer_rows

            report._rows = fake_rows
            snapshots, retailers = collect_inventory_link_health("2026-06-24T00:00:00Z")
        finally:
            report._rows = original_rows

        self.assertEqual([item["region"] for item in snapshots], ["EU", "AU", "ID"])
        self.assertEqual([(item["region"], item["retailer_name"]) for item in retailers], [("EU", "Alpha"), ("AU", "Zulu"), ("ID", "Beta")])
        self.assertTrue(any("dbo.RetailerInventory" in query for query in calls))
        self.assertTrue(any("dbo.Retailers" in query for query in calls))

    def test_inactive_rows_are_excluded_from_aggregates(self):
        active_rows = [
            {"RegionCode": "EU", "TotalRows": 3, "LinkedModelRows": 2, "LinkedSizeRows": 1, "RetailerCount": 1},
        ]
        retailer_rows = [
            {"RegionCode": "EU", "RetailerName": "Active Shop", "TotalRows": 3, "LinkedModelRows": 2, "LinkedSizeRows": 1},
        ]

        from observability import inventory_link_health as report

        original_rows = report._rows
        try:
            calls = []

            def fake_rows(query):
                calls.append(query)
                return active_rows if len(calls) == 1 else retailer_rows

            report._rows = fake_rows
            snapshots, retailers = collect_inventory_link_health("2026-06-24T00:00:00Z")
        finally:
            report._rows = original_rows

        self.assertEqual(snapshots[0]["total_rows"], 3)
        self.assertEqual(snapshots[0]["canonical_size_linked_rows"], 1)
        self.assertEqual(retailers[0]["total_rows"], 3)
        self.assertEqual(retailers[0]["canonical_size_linked_rows"], 1)


if __name__ == "__main__":
    unittest.main()
