import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import importlib

from scripts.europe import run_eu_retailer_inventory_refresh as retailer_runner
from scripts.manufacturer_availability import (
    run_eu_manufacturer_availability_pipeline as mfa_runner,
)


ROOT = Path(__file__).resolve().parents[1]


class EuScheduledRuntimeGuardrailTests(unittest.TestCase):
    def test_retailer_runner_rejects_non_eu_region(self):
        with patch.dict(os.environ, {"QUIVRR_REGION_CODE": "AU"}):
            with self.assertRaisesRegex(RuntimeError, "expected 'EU'"):
                retailer_runner.assert_region_scope()

    def test_retailer_runner_rejects_detail_fetch_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(
                json.dumps({"results": [{"target": "mundo_surf", "detailFetchFailures": 1}]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "mundo_surf"):
                retailer_runner.assert_detail_fetch_health(path)

    def test_retailer_runner_allows_bounded_detail_fetch_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "target": "mundo_surf",
                                "detailFetchFailures": 16,
                                "productsAccepted": 4854,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            retailer_runner.assert_detail_fetch_health(path)

    def test_shopify_rollout_targets_remain_eu_scoped(self):
        module = importlib.import_module("scrapers.retailers.europe.run_eu_retailer_discovery")
        self.assertTrue(
            {
                "board_exchange",
                "pop_up_surf_shop",
                "noordzee_boardstore",
                "gsi_europe",
                "hart_beach",
            }.issubset(module.SHOPIFY_TARGETS)
        )

        targets = json.loads(
            (ROOT / "scrapers/retailers/europe/shopify/eu_shopify_targets.json").read_text(
                encoding="utf-8"
            )
        )
        by_slug = {target["retailerSlug"]: target for target in targets}
        for slug in [
            "board_exchange",
            "pop_up_surf_shop",
            "noordzee_boardstore",
            "gsi_europe",
            "hart_beach",
        ]:
            with self.subTest(slug=slug):
                self.assertEqual(by_slug[slug]["regionCode"], "EU")
                self.assertTrue(by_slug[slug]["enabled"])

    def test_custom_rollout_targets_remain_eu_scoped(self):
        module = importlib.import_module("scrapers.retailers.europe.run_eu_retailer_discovery")
        self.assertIn("tablas_surf_shop", module.CUSTOM_TARGETS)

        targets = json.loads(
            (ROOT / "scrapers/retailers/europe/custom/eu_custom_targets.json").read_text(
                encoding="utf-8"
            )
        )
        by_slug = {target["retailerSlug"]: target for target in targets}
        self.assertEqual(by_slug["tablas_surf_shop"]["regionCode"], "EU")
        self.assertTrue(by_slug["tablas_surf_shop"]["enabled"])

    def test_mfa_runner_rejects_non_eu_region(self):
        with patch.dict(os.environ, {"QUIVRR_REGION_CODE": "ID"}):
            with self.assertRaisesRegex(RuntimeError, "expected 'EU'"):
                mfa_runner.assert_region_scope()

    def test_scheduled_mfa_brand_allowlist_is_reviewed_set(self):
        self.assertEqual(
            mfa_runner.APPROVED_BRANDS,
            {
                "js_industries": "JS Industries",
                "pyzel": "Pyzel",
                "firewire": "Firewire",
                "haydenshapes": "Haydenshapes",
                "rusty": "Rusty",
                "sharp_eye": "Sharp Eye",
                "dhd": "DHD",
            },
        )

    def test_mfa_import_delete_is_eu_brand_and_source_scoped(self):
        source = (
            ROOT / "scripts/manufacturer_availability/import_eu_manufacturer_availability.py"
        ).read_text(encoding="utf-8")
        self.assertIn("WHERE BrandId = :brand_id", source)
        self.assertIn("AND RegionCode = 'EU'", source)
        self.assertIn("AND AvailabilitySource = 'manufacturer_direct'", source)
        self.assertIn('"RegionCode": REGION', source)

    def test_azure_setup_targets_only_eu_jobs_and_secret_refs(self):
        source = (ROOT / "scripts/azure/create_eu_container_jobs.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn('Name = "quivrr-nightly-eu-inventory"', source)
        self.assertIn('Name = "quivrr-eu-mfr-availability"', source)
        self.assertNotIn("quivrr-nightly-au-inventory", source)
        self.assertNotIn('Name = "quivrr-mfr-availability"', source)
        self.assertIn('"SQL_PASSWORD=secretref:sql-password"', source)
        self.assertNotRegex(source, r"SQL_PASSWORD=[^s$\"]")


if __name__ == "__main__":
    unittest.main()
