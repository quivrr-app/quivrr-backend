import unittest

from scripts.dealers import discover_global_dealer_network as discovery


class DealerNetworkDiscoveryTests(unittest.TestCase):
    def test_normalise_dealer_name_collapses_suffixes(self):
        self.assertEqual(
            discovery.normalise_dealer_name("Jack's Surfboards - Huntington Beach"),
            "jack s huntington beach",
        )

    def test_infer_region_code_handles_core_and_optional_regions(self):
        self.assertEqual(discovery.infer_region_code("Australia", "NSW"), "AU")
        self.assertEqual(discovery.infer_region_code("Portugal", None), "EU")
        self.assertEqual(discovery.infer_region_code("United States", "Hawaii"), "HI")
        self.assertEqual(discovery.infer_region_code("Puerto Rico", None), "PR")

    def test_classify_status_respects_running_and_candidates(self):
        current = {
            "domain:surfstationstore.com": discovery.CurrentRetailer(
                retailer_name="Surf Station",
                website="https://www.surfstationstore.com",
                platform="shopify",
                configured=True,
                enabled=True,
                region_code="US",
                source_file="test",
                active_rows=222,
            ),
            "domain:hansensurf.com": discovery.CurrentRetailer(
                retailer_name="Hansen Surfboards",
                website="https://www.hansensurf.com",
                platform="shopify",
                configured=True,
                enabled=False,
                region_code="US",
                source_file="test",
            ),
        }
        self.assertEqual(
            discovery.classify_status(
                {
                    "dealerName": "Surf Station",
                    "website": "https://www.surfstationstore.com",
                },
                current,
            ),
            "Already running",
        )
        self.assertEqual(
            discovery.classify_status(
                {
                    "dealerName": "Hansen Surfboards",
                    "website": "https://www.hansensurf.com",
                },
                current,
            ),
            "Known but disabled",
        )
        self.assertEqual(
            discovery.classify_status(
                {
                    "dealerName": "Unknown Candidate",
                    "website": "https://example.com",
                },
                current,
            ),
            "Candidate",
        )

    def test_score_dealer_prefers_high_priority_region_candidates(self):
        entry = {
            "status": "Candidate",
            "regionCode": "US",
            "manufacturers": ["Haydenshapes", "JS Industries"],
            "website": "https://example.com",
            "dealerType": "online_store",
        }
        self.assertEqual(discovery.score_dealer(entry), 5)


if __name__ == "__main__":
    unittest.main()
