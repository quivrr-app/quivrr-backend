import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.manufacturer_availability import run_us_manufacturer_availability_pipeline as mfa_runner
from scripts.usa import run_us_retailer_inventory_refresh as retailer_runner


ROOT = Path(__file__).resolve().parents[1]


class UsRegionalRolloutTests(unittest.TestCase):
    def test_retailer_runner_rejects_non_us_region(self):
        with patch.dict(os.environ, {"QUIVRR_REGION_CODE": "EU"}):
            with self.assertRaisesRegex(RuntimeError, "expected 'US'"):
                retailer_runner.assert_region_scope()

    def test_mfa_runner_rejects_non_us_region(self):
        with patch.dict(os.environ, {"QUIVRR_REGION_CODE": "AU"}):
            with self.assertRaisesRegex(RuntimeError, "expected 'US'"):
                mfa_runner.assert_region_scope()

    def test_search_region_validation_accepts_us(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('{"AU", "ID", "EU", "US"}', source)

    def test_us_master_targets_are_region_scoped(self):
        targets = json.loads(
            (ROOT / "scrapers/retailers/usa/us_retailer_targets.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(targets), 12)
        for target in targets:
            with self.subTest(slug=target["retailerSlug"]):
                self.assertEqual(target["regionCode"], "US")

    def test_enabled_us_shopify_targets_are_region_scoped(self):
        targets = json.loads(
            (ROOT / "scrapers/retailers/usa/shopify/us_shopify_targets.json").read_text(
                encoding="utf-8"
            )
        )
        expected = {
            "surf_station",
            "jacks_surfboards",
            "real_watersports",
            "cleanline_surf",
            "hansen_surfboards",
            "hawaiian_south_shore",
            "encinitas_surfboards",
            "birds_surf_shed",
        }
        self.assertEqual({target["retailerSlug"] for target in targets}, expected)
        for target in targets:
            with self.subTest(slug=target["retailerSlug"]):
                self.assertEqual(target["regionCode"], "US")
                self.assertTrue(target["enabled"])
                self.assertEqual(target["priceCurrency"], "USD")

    def test_us_manufacturer_plan_covers_requested_sources(self):
        payload = json.loads(
            (
                ROOT
                / "scrapers/manufacturers/availability/config/us_manufacturer_availability_targets.example.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(payload["regionCode"], "US")
        self.assertFalse(payload["enabled"])
        self.assertEqual(
            {target["brandName"] for target in payload["targets"]},
            set(mfa_runner.APPROVED_BRANDS.keys()),
        )


if __name__ == "__main__":
    unittest.main()
