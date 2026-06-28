import unittest

from scrapers.retailers import scrape_coopers_inventory


class CoopersInventoryScraperTests(unittest.TestCase):
    def test_obvious_accessory_urls_are_skipped_early(self):
        self.assertTrue(
            scrape_coopers_inventory.is_obvious_accessory_url(
                "https://coopersboardstore.com.au/product/all-round-essential-leash-6/"
            )
        )
        self.assertTrue(
            scrape_coopers_inventory.is_obvious_accessory_url(
                "https://coopersboardstore.com.au/product/carissa-moore-signature-tri-fin-set/"
            )
        )

    def test_real_board_urls_are_not_skipped(self):
        self.assertFalse(
            scrape_coopers_inventory.is_obvious_accessory_url(
                "https://coopersboardstore.com.au/product/aloha-habanero-ii-pu/"
            )
        )
        self.assertFalse(
            scrape_coopers_inventory.is_obvious_accessory_url(
                "https://coopersboardstore.com.au/product/chopped-log-single-fin/"
            )
        )
        self.assertFalse(
            scrape_coopers_inventory.is_obvious_accessory_url(
                "https://coopersboardstore.com.au/product/mid-tide-pu/"
            )
        )


if __name__ == "__main__":
    unittest.main()
