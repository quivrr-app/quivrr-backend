import unittest

from scrapers.products import bigcommerce_scraper
from scrapers.products import normalise_surfboards
from scrapers.retailers import build_active_scrape_targets


class AuBigCommercePackTests(unittest.TestCase):
    def test_trigger_bros_target_gets_manual_category_urls(self):
        target = build_active_scrape_targets.build_target(
            {
                "primary_name": "Trigger Bros Surfboards",
                "website": "https://triggerbrothers.com.au",
                "country": "Australia",
                "platform": "bigcommerce",
                "priority": 1,
            },
            overrides={},
        )
        self.assertEqual(
            target["category_urls"],
            [
                "https://triggerbrothers.com.au/surf/boards/",
                "https://triggerbrothers.com.au/store/surf/used-surfboards/",
            ],
        )

    def test_surf_shops_australia_stays_out_of_active_targets(self):
        reason = build_active_scrape_targets.get_exclusion_reason(
            {
                "primary_name": "Surf Shops Australia",
                "website": "https://surfshopsaustralia.com.au",
                "country": "Australia",
                "platform": "bigcommerce",
                "hardboards": True,
            },
            overrides={},
        )
        self.assertEqual(reason, "awaiting_bigcommerce_revalidation")

    def test_existing_manual_targets_are_preserved_when_regenerating(self):
        grouped = {
            "https://triggerbrothers.com.au": {
                "primary_name": "Trigger Bros Surfboards",
                "website": "https://triggerbrothers.com.au",
                "website_key": "https://triggerbrothers.com.au",
                "country": "Australia",
                "platform": "bigcommerce",
                "status": "active",
                "priority": 1,
                "locations": [],
                "source": "retailer_detection_pipeline",
            }
        }
        existing_targets = [
            {
                "primary_name": "Surfection Mosman",
                "website": "https://surfectionmosman.com",
                "website_key": "https://surfectionmosman.com",
                "country": "Australia",
                "platform": "shopify",
                "status": "active",
                "priority": 1,
                "collection_handles": ["js-industries", "channel-islands"],
                "locations": [],
                "source": "manual_final_retailer_onboarding",
            },
            {
                "primary_name": "Saltwater Wine Port Macquarie",
                "website": "https://saltwaterwine.com.au",
                "website_key": "https://saltwaterwine.com.au",
                "country": "Australia",
                "platform": "shopify",
                "status": "active",
                "priority": 3,
                "locations": [],
                "source": "retailer_detection_pipeline",
            },
        ]

        preserved = build_active_scrape_targets.merge_existing_targets(
            grouped,
            existing_targets,
            overrides={},
        )

        self.assertIn("https://surfectionmosman.com", grouped)
        self.assertEqual(
            grouped["https://surfectionmosman.com"]["collection_handles"],
            ["js-industries", "channel-islands"],
        )
        self.assertNotIn("https://saltwaterwine.com.au", grouped)
        self.assertEqual(preserved, ["https://surfectionmosman.com"])

    def test_new_unapproved_targets_do_not_auto_activate(self):
        self.assertFalse(
            build_active_scrape_targets.should_activate_target(
                "https://sds.com.au",
                {
                    "https://triggerbrothers.com.au",
                    "https://boardcollective.com.au",
                },
            )
        )
        self.assertTrue(
            build_active_scrape_targets.should_activate_target(
                "https://triggerbrothers.com.au",
                {
                    "https://boardcollective.com.au",
                },
            )
        )

    def test_bigcommerce_card_links_are_resolved_and_deduped(self):
        html = """
        <html>
          <body>
            <div class="card">
              <h3 class="card-title">
                <a href="/trigger-bros-glider-11ft-surfboard-orange-spray/">Trigger Bros Glider</a>
              </h3>
              <a class="card-figure" href="/trigger-bros-glider-11ft-surfboard-orange-spray/"></a>
            </div>
            <div class="card">
              <h3 class="card-title">
                <a href="/used-surfboard-ub303-trigger-bros-twin-fin/">Used Surfboard UB303 Trigger Bros Twin Fin</a>
              </h3>
            </div>
          </body>
        </html>
        """
        links = bigcommerce_scraper.extract_card_product_links(
            html,
            "https://triggerbrothers.com.au/surf/boards/",
        )
        self.assertEqual(
            links,
            [
                "https://triggerbrothers.com.au/trigger-bros-glider-11ft-surfboard-orange-spray/",
                "https://triggerbrothers.com.au/used-surfboard-ub303-trigger-bros-twin-fin/",
            ],
        )

    def test_product_page_fallback_captures_description_and_stock(self):
        html = """
        <html>
          <head>
            <title>Trigger Bros Glider 11ft Surfboard Orange Spray</title>
            <meta property="og:image" content="https://cdn.example.com/glider.jpg" />
            <meta property="product:price:amount" content="1650.00" />
          </head>
          <body>
            <h1>Trigger Bros Glider 11ft Surfboard Orange Spray</h1>
            <div class="productView-description">
              Product Features Dimensions: 11' x 23.5" x 3.5" Volume: 110 Lt
            </div>
            <div>Availability: In Stock</div>
          </body>
        </html>
        """
        retailer = {
            "primary_name": "Trigger Bros Surfboards",
            "website": "https://triggerbrothers.com.au",
            "platform": "bigcommerce",
        }
        rows = bigcommerce_scraper.extract_product_from_page(
            "https://triggerbrothers.com.au/trigger-bros-glider-11ft-surfboard-orange-spray/",
            retailer,
            html,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["price"], "1650.00")
        self.assertTrue(rows[0]["available"])
        self.assertIn("11' x 23.5", rows[0]["description"])
        self.assertEqual(rows[0]["images"], ["https://cdn.example.com/glider.jpg"])

    def test_normaliser_can_extract_dimensions_from_trigger_bros_description(self):
        description = 'Description Product Features Dimensions: 11\' x 23.5" x 3.5" Volume: 110 Lt Single Fin 10"'
        dimensions = normalise_surfboards.extract_dimensions(description)
        volume = normalise_surfboards.extract_volume(description)
        self.assertEqual(
            dimensions,
            {
                "length": "11'0",
                "width": "23.5",
                "thickness": "3.5",
            },
        )
        self.assertEqual(volume, 110.0)


if __name__ == "__main__":
    unittest.main()
