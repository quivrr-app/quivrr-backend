import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.manufacturer_availability import run_us_manufacturer_availability_pipeline as mfa_runner
from scripts.usa import import_us_retailer_inventory as us_importer
from scripts.usa import run_us_retailer_inventory_refresh as retailer_runner
from scrapers.retailers.usa.bigcommerce import discover_us_bigcommerce_products as bigcommerce_discovery
from scrapers.retailers.usa.magento import discover_us_magento_products as magento_discovery
from scrapers.retailers.usa.shopify import discover_us_shopify_products as shopify_discovery
from scrapers.retailers.usa.woocommerce import discover_us_woocommerce_products as woocommerce_discovery


ROOT = Path(__file__).resolve().parents[1]


class UsRegionalRolloutTests(unittest.TestCase):
    EXPECTED_ENABLED_SHOPIFY = {
        "surf_station",
        "jacks_surfboards",
        "real_watersports",
        "cleanline_surf",
        "hawaiian_south_shore",
        "birds_surf_shed",
        "island_water_sports",
        "surf_n_sea",
        "kimos_surf_hut",
        "moment_surf_co",
        "degree_33_surfboards",
        "surfboard_broker",
        "infinity_surfboards",
        "walden_surfboards",
        "stewart_surfboards",
        "bing_surfboards",
        "robert_august_surf_company",
        "dark_arts_surf",
    }
    EXPECTED_ENABLED_BIGCOMMERCE = {"catalyst_surf_shop"}
    EXPECTED_ENABLED_MAGENTO = {"warm_winds"}

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
        self.assertEqual(len(targets), 25)
        for target in targets:
            with self.subTest(slug=target["retailerSlug"]):
                self.assertEqual(target["regionCode"], "US")

    def test_enabled_us_shopify_targets_are_region_scoped(self):
        targets = json.loads(
            (ROOT / "scrapers/retailers/usa/shopify/us_shopify_targets.json").read_text(
                encoding="utf-8"
            )
        )
        enabled_targets = [target for target in targets if target["enabled"]]
        self.assertEqual(
            {target["retailerSlug"] for target in enabled_targets},
            self.EXPECTED_ENABLED_SHOPIFY,
        )
        for target in enabled_targets:
            with self.subTest(slug=target["retailerSlug"]):
                self.assertEqual(target["regionCode"], "US")
                self.assertTrue(target["enabled"])
                self.assertEqual(target["priceCurrency"], "USD")

    def test_us_candidate_backlog_is_region_scoped(self):
        targets = json.loads(
            (
                ROOT / "scrapers/retailers/usa/us_retailer_candidate_backlog.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(len(targets), 45)
        self.assertEqual(
            len({target["retailerSlug"] for target in targets}),
            len(targets),
            "Candidate backlog should not contain duplicate retailer slugs.",
        )
        for target in targets:
            with self.subTest(slug=target["retailerSlug"]):
                self.assertEqual(target["regionCode"], "US")
                self.assertFalse(target["runnable"])
                self.assertIn(
                    target["detectedPlatform"],
                    {"shopify", "woocommerce", "magento", "unknown"},
                )
                self.assertIn(
                    target["platformDetectionStatus"],
                    {"needs_review", "opaque", "blocked"},
                )

    def test_shopify_backlog_entries_remain_non_runnable(self):
        targets = json.loads(
            (
                ROOT / "scrapers/retailers/usa/us_retailer_candidate_backlog.json"
            ).read_text(encoding="utf-8")
        )
        shopify_backlog = [
            target for target in targets if target["detectedPlatform"] == "shopify"
        ]
        self.assertTrue(shopify_backlog)
        for target in shopify_backlog:
            with self.subTest(slug=target["retailerSlug"]):
                self.assertFalse(target["runnable"])
                self.assertNotIn(target["retailerSlug"], self.EXPECTED_ENABLED_SHOPIFY)

    def test_us_shopify_dry_run_metadata_includes_promoted_targets(self):
        targets = shopify_discovery.load_targets()
        report = shopify_discovery.build_dry_run_report(targets)
        enabled = {
            target["retailerSlug"]
            for target in report["targets"]
            if target["enabled"] is True
        }
        self.assertTrue(self.EXPECTED_ENABLED_SHOPIFY.issubset(enabled))

    def test_us_bigcommerce_targets_are_region_scoped(self):
        targets = bigcommerce_discovery.load_targets()
        enabled = {target["retailerSlug"] for target in targets if target["enabled"] is True}
        self.assertEqual(enabled, self.EXPECTED_ENABLED_BIGCOMMERCE)
        for target in targets:
            with self.subTest(slug=target["retailerSlug"]):
                self.assertEqual(target["regionCode"], "US")
                self.assertEqual(target["platform"], "bigcommerce")

    def test_us_magento_targets_are_region_scoped(self):
        targets = magento_discovery.load_targets()
        enabled = {target["retailerSlug"] for target in targets if target["enabled"] is True}
        self.assertEqual(enabled, self.EXPECTED_ENABLED_MAGENTO)
        for target in targets:
            with self.subTest(slug=target["retailerSlug"]):
                self.assertEqual(target["regionCode"], "US")
                self.assertEqual(target["platform"], "magento")

    def test_us_woocommerce_targets_are_region_scoped(self):
        targets = woocommerce_discovery.load_targets()
        self.assertEqual(len(targets), 3)
        self.assertFalse(any(target["enabled"] for target in targets))
        for target in targets:
            with self.subTest(slug=target["retailerSlug"]):
                self.assertEqual(target["regionCode"], "US")
                self.assertEqual(target["platform"], "woocommerce")

    def test_disabled_us_follow_up_targets_remain_disabled(self):
        targets = json.loads(
            (ROOT / "scrapers/retailers/usa/us_retailer_targets.json").read_text(
                encoding="utf-8"
            )
        )
        disabled = {target["retailerSlug"] for target in targets if not target["enabled"]}
        self.assertIn("hansen_surfboards", disabled)
        self.assertIn("encinitas_surfboards", disabled)
        self.assertIn("et_surf", disabled)

    def test_us_retailer_apply_mode_requires_confirmation(self):
        with patch.object(retailer_runner, "emit_event"), patch.object(
            retailer_runner, "update_job_state"
        ), patch.object(retailer_runner, "assert_region_scope"):
            with patch("sys.argv", ["run_us_retailer_inventory_refresh.py", "apply"]):
                with self.assertRaisesRegex(RuntimeError, "requires explicit confirmation"):
                    retailer_runner.main()

    def test_us_importer_apply_mode_requires_confirmation(self):
        with patch("sys.argv", ["import_us_retailer_inventory.py", "--apply"]):
            with self.assertRaisesRegex(RuntimeError, "requires explicit confirmation"):
                us_importer.main()

    def test_us_retailer_dry_run_reports_summary_without_sql(self):
        rows = [
            {
                "retailerSlug": "surf_station",
                "retailerName": "Surf Station",
                "regionCode": "US",
                "rawProductTitle": "Board One",
                "productUrl": "https://example.com/1",
                "productImageUrl": "https://example.com/1.jpg",
                "priceAmount": "799.00",
                "priceCurrency": "USD",
                "stockStatus": "in_stock",
                "lengthFeetInches": "6'0",
                "volumeLitres": 30.1,
                "importableRaw": True,
            },
            {
                "retailerSlug": "catalyst_surf_shop",
                "retailerName": "Catalyst Surf Shop",
                "regionCode": "US",
                "rawProductTitle": "Board BigCommerce",
                "productUrl": "https://example.com/catalyst",
                "productImageUrl": "https://example.com/catalyst.jpg",
                "priceAmount": "1049.00",
                "priceCurrency": "USD",
                "stockStatus": "in_stock",
                "lengthFeetInches": "6'4",
                "volumeLitres": 35.2,
                "importableRaw": True,
            },
            {
                "retailerSlug": "warm_winds",
                "retailerName": "Warm Winds",
                "regionCode": "US",
                "rawProductTitle": "Board Magento",
                "productUrl": "https://example.com/warm",
                "productImageUrl": "https://example.com/warm.jpg",
                "priceAmount": "745.00",
                "priceCurrency": "USD",
                "stockStatus": "in_stock",
                "lengthFeetInches": "5'11",
                "volumeLitres": 31.8,
                "importableRaw": True,
            },
            {
                "retailerSlug": "moment_surf_co",
                "retailerName": "Moment Surf Co",
                "regionCode": "US",
                "rawProductTitle": "Board One Point Two",
                "productUrl": "https://example.com/1b",
                "productImageUrl": "https://example.com/1b.jpg",
                "priceAmount": "899.00",
                "priceCurrency": "USD",
                "stockStatus": "in_stock",
                "lengthFeetInches": "6'2",
                "volumeLitres": 31.4,
                "importableRaw": True,
            },
            {
                "retailerSlug": "dark_arts_surf",
                "retailerName": "Dark Arts Surf",
                "regionCode": "US",
                "rawProductTitle": "Board One Point Three",
                "productUrl": "https://example.com/1c",
                "productImageUrl": "https://example.com/1c.jpg",
                "priceAmount": "999.00",
                "priceCurrency": "USD",
                "stockStatus": "in_stock",
                "lengthFeetInches": "5'11",
                "volumeLitres": 29.7,
                "importableRaw": True,
            },
            {
                "retailerSlug": "birds_surf_shed",
                "retailerName": "Bird's Surf Shed",
                "regionCode": "US",
                "rawProductTitle": "Board Two",
                "productUrl": "https://example.com/2",
                "productImageUrl": "",
                "priceAmount": "699.00",
                "priceCurrency": "USD",
                "stockStatus": "in_stock",
                "lengthFeetInches": "",
                "volumeLitres": 28.4,
                "importableRaw": False,
            },
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "us_normalised_inventory.json"
            input_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
            buffer = StringIO()
            with patch.dict(
                retailer_runner.MINIMUM_ROWS,
                {
                    "surf_station": 1,
                    "catalyst_surf_shop": 1,
                    "warm_winds": 1,
                    "moment_surf_co": 1,
                    "dark_arts_surf": 1,
                    "birds_surf_shed": 1,
                },
                clear=True,
            ), patch.object(retailer_runner, "emit_event"), patch.object(
                retailer_runner, "update_job_state"
            ) as update_job_state, patch.object(
                retailer_runner, "assert_region_scope"
            ), patch(
                "sys.argv",
                [
                    "run_us_retailer_inventory_refresh.py",
                    "--skip-discovery",
                    "--input",
                    str(input_path),
                ],
            ), redirect_stdout(buffer):
                retailer_runner.main()
            output = buffer.getvalue()
            self.assertIn("US retailer readiness summary:", output)
            update_job_state.assert_called_once()
            self.assertIn('"catalyst_surf_shop": 1', output)
            self.assertIn('"warm_winds": 1', output)
            self.assertIn('"moment_surf_co": 1', output)
            self.assertIn('"dark_arts_surf": 1', output)

    def test_us_mfa_dry_run_writes_rollout_report_without_sql(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "us_mfa_rollout_plan.json"
            buffer = StringIO()
            with patch.object(mfa_runner, "emit_event"), patch.object(
                mfa_runner, "update_job_state"
            ) as update_job_state, patch.object(
                mfa_runner, "assert_region_scope"
            ), patch.object(
                mfa_runner, "REPORT_OUTPUT", report_path
            ), patch(
                "sys.argv",
                ["run_us_manufacturer_availability_pipeline.py", "dry-run"],
            ), redirect_stdout(buffer):
                mfa_runner.main()
            self.assertTrue(report_path.exists())
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["regionCode"], "US")
            self.assertIn("Album", {brand["brandName"] for brand in payload["brands"]})
            update_job_state.assert_called_once()

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
