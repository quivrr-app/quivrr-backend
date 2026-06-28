import unittest

from scrapers.retailers import build_active_scrape_targets as active_targets
from scripts.tools import build_retailer_governance_audit as governance_audit


class AuShopifyPackGuardrailsTests(unittest.TestCase):
    def test_awsm_surf_uses_second_hand_board_collection_hint(self):
        target = active_targets.build_target(
            {
                "primary_name": "AWSM Surf",
                "website": "https://awsmsurf.com",
                "country": "Australia",
                "platform": "shopify",
                "priority": 1,
            },
            {},
        )
        self.assertEqual(target.get("collection_handles"), ["second-hand-surfboard"])

    def test_overboard_surf_uses_board_collection_hint(self):
        target = active_targets.build_target(
            {
                "primary_name": "Overboard Surf",
                "website": "https://overboardsurf.com.au",
                "country": "Australia",
                "platform": "shopify",
                "priority": 2,
            },
            {},
        )
        self.assertEqual(target.get("collection_handles"), ["boards"])

    def test_board_collective_shell_retailers_are_excluded_from_active_targets(self):
        for retailer_name in (
            "Red Herring Surf",
            "Saltwater Wine Port Macquarie",
        ):
            with self.subTest(retailer_name=retailer_name):
                reason = active_targets.get_exclusion_reason(
                    {
                        "primary_name": retailer_name,
                        "country": "Australia",
                        "platform": "shopify",
                        "hardboards": True,
                    },
                    {},
                )
                self.assertEqual(reason, "board_collective_shell_duplicate")

    def test_governance_audit_marks_board_collective_shells_as_business_disabled(self):
        for retailer_slug in (
            "red_herring_surf",
            "saltwater_wine_port_macquarie",
        ):
            with self.subTest(retailer_slug=retailer_slug):
                status, reason = governance_audit.classify(
                    {
                        "retailer_slug": retailer_slug,
                        "health": "missing",
                        "raw_products": 0,
                        "verified_surfboards": 0,
                        "available_inventory": 0,
                    }
                )
                self.assertEqual(status, "business_disabled")
                self.assertIn("Board Collective storefront shell", reason)


if __name__ == "__main__":
    unittest.main()
