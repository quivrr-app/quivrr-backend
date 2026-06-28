import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scrapers.retailers.discovery import engine
from scripts.dealers import build_au_coverage_factory_report as report_builder


class AuRetailerDiscoveryEngineTests(unittest.TestCase):
    def test_detect_board_collective_duplicate_shell(self):
        html = """
        <html>
          <body>
            <a href="https://boardcollective.com.au/products/demo-board">Board</a>
          </body>
        </html>
        """
        duplicate_of = engine.detect_board_collective_shell(
            "https://redherringsurf.com.au",
            html,
            ["https://boardcollective.com.au/products/demo-board"],
        )
        self.assertEqual(duplicate_of, "Board Collective")

    def test_detect_platform_from_bigcommerce_html(self):
        html = '<html><script src="https://cdn11.bigcommerce.com/s-abc/latest.js"></script></html>'
        empty_probe = engine.FetchResult(url="https://triggerbrothers.com.au", status_code=404, text="", headers={})
        with mock.patch.object(engine, "fetch_text", return_value=empty_probe):
            detected = engine.detect_platform_from_html("https://triggerbrothers.com.au", html)
        self.assertEqual(detected["platform"], "bigcommerce")
        self.assertEqual(detected["status"], "ready_bigcommerce")

    def test_discover_board_category_urls_prefers_board_surfaces(self):
        html = """
        <html>
          <body>
            <a href="/collections/surfboards">Surfboards</a>
            <a href="/collections/wetsuits">Wetsuits</a>
            <a href="/surfboards/shortboards">Shortboards</a>
          </body>
        </html>
        """
        client = mock.Mock()
        with mock.patch.object(engine, "probe_category_urls", return_value=[]):
            urls = engine.discover_board_category_urls(client, "https://example.com", html)
        self.assertIn("https://example.com/collections/surfboards", urls)
        self.assertIn("https://example.com/surfboards/shortboards", urls)

    def test_extract_product_candidates_discovers_board_product_urls(self):
        html = """
        <html>
          <body>
            <article class="product">
              <a href="/products/album-bom-dia-56">Album Bom Dia 5'6 Surfboard</a>
              <img src="/images/bom-dia.jpg" />
              <span>$1,099.00</span>
              <span>In stock</span>
            </article>
            <article class="product">
              <a href="/products/futures-fins">Futures Fins</a>
            </article>
          </body>
        </html>
        """
        products = engine.extract_product_candidates_from_html(html, "https://example.com/collections/surfboards")
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["productUrl"], "https://example.com/products/album-bom-dia-56")
        self.assertEqual(products[0]["priceAmount"], "1099.00")

    def test_extract_supported_brand_signals(self):
        brands = engine.extract_supported_brand_signals("JS Monsta 10 by JS Industries", "Album Bom Dia", "Pyzel Ghost")
        self.assertIn("JS Industries", brands)
        self.assertIn("Album", brands)
        self.assertIn("Pyzel", brands)

    def test_classify_discovery_result_promotes_bigcommerce_candidate(self):
        result = engine.classify_discovery_result(
            {
                "dealerName": "Trigger Bros Surfboards",
                "website": "https://triggerbrothers.com.au",
                "detectedPlatform": "bigcommerce",
                "currentStatus": "manual_review",
                "boardCategoryUrls": ["https://triggerbrothers.com.au/store/surf/used-surfboards/"],
                "productUrlExamples": ["https://triggerbrothers.com.au/trigger-bros-hot-dog-stubby-9ft-surfboard-red/"],
                "approxBoardProductCount": 24,
                "supportedBrandSignals": ["JS Industries", "Pyzel"],
                "priceVisible": True,
                "stockVisible": True,
                "imagesVisible": True,
                "dimensionsVisible": True,
                "volumeVisible": False,
                "paginationDetected": True,
                "duplicateOf": "",
                "blockedReason": "",
            }
        )
        self.assertEqual(result["recommendedStatus"], "ready_bigcommerce")
        self.assertEqual(result["confidence"], "high")
        self.assertGreater(result["priorityScore"], 40)

    def test_classify_discovery_result_keeps_non_au_surface_in_review(self):
        result = engine.classify_discovery_result(
            {
                "dealerName": "City Beach",
                "website": "https://www.citybeach.com",
                "detectedPlatform": "magento",
                "currentStatus": "manual_review",
                "boardCategoryUrls": ["https://www.citybeach.com/us/kids/boardsports/"],
                "productUrlExamples": ["https://www.citybeach.com/us/demo-board"],
                "approxBoardProductCount": 20,
                "supportedBrandSignals": ["Channel Islands"],
                "priceVisible": True,
                "stockVisible": True,
                "imagesVisible": True,
                "dimensionsVisible": True,
                "volumeVisible": False,
                "paginationDetected": True,
                "duplicateOf": "",
                "blockedReason": "",
            }
        )
        self.assertEqual(result["recommendedStatus"], "manual_review")
        self.assertEqual(result["manualReviewReason"], "non_au_catalogue_surface")

    def test_coverage_report_uses_discovery_results_when_present(self):
        sample_report = {
            "results": [
                {
                    "dealerName": "Bells Beach Surf Shop",
                    "website": "https://bellsbeachsurfshop.com.au",
                    "detectedPlatform": "bigcommerce",
                    "recommendedStatus": "ready_bigcommerce",
                    "boardCategoryUrls": ["https://bellsbeachsurfshop.com.au/surfboards"],
                    "productUrlExamples": ["https://bellsbeachsurfshop.com.au/products/demo-board"],
                    "approxBoardProductCount": 18,
                    "supportedBrandSignals": ["Pyzel"],
                    "priceVisible": True,
                    "stockVisible": True,
                    "imagesVisible": True,
                    "paginationDetected": True,
                    "priorityScore": 91,
                    "recommendedAction": "Candidate for the reusable AU BigCommerce pack.",
                    "manualReviewReason": "",
                    "notes": "Synthetic test discovery output.",
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "au_retailer_discovery_report.json"
            report_path.write_text(json.dumps(sample_report), encoding="utf-8")
            original = report_builder.DISCOVERY_REPORT
            try:
                report_builder.DISCOVERY_REPORT = report_path
                rows = report_builder.build_candidate_rows(include_discovery=True)
            finally:
                report_builder.DISCOVERY_REPORT = original

        bells = next(row for row in rows if row["dealerName"] == "Bells Beach Surf Shop")
        self.assertEqual(bells["status"], "ready_bigcommerce")
        self.assertEqual(bells["platform"], "bigcommerce")
        self.assertEqual(bells["approxBoardProductCount"], 18)


if __name__ == "__main__":
    unittest.main()
