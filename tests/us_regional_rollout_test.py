import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
from unittest.mock import Mock, patch

from scrapers.manufacturers.availability.us import build_us_shopify_availability as us_mfa_builder
from scrapers.manufacturers.availability.us import (
    us_mfa_additional_sources as us_mfa_additional,
)
from scripts.manufacturer_availability import import_us_manufacturer_availability as us_mfa_importer
from scripts.manufacturer_availability import run_us_manufacturer_availability_pipeline as mfa_runner
from scripts.usa import import_us_retailer_inventory as us_importer
from scripts.usa import run_us_retailer_inventory_refresh as retailer_runner
from scrapers.retailers.usa.bigcommerce import discover_us_bigcommerce_products as bigcommerce_discovery
from scrapers.retailers.usa.magento import discover_us_magento_products as magento_discovery
from scrapers.retailers.usa.shopify import discover_us_shopify_products as shopify_discovery
from scrapers.retailers.usa.woocommerce import discover_us_woocommerce_products as woocommerce_discovery
from utils.manufacturer_shipping import shipping_metadata_for_brand


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

    def test_us_mfa_importer_apply_mode_requires_confirmation(self):
        with patch("sys.argv", ["import_us_manufacturer_availability.py", "--apply"]):
            with self.assertRaisesRegex(RuntimeError, "requires explicit confirmation"):
                us_mfa_importer.main()

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
            ), patch.object(
                mfa_runner,
                "region_counts",
                side_effect=[
                    {"AU": 1, "EU": 1, "ID": 1, "US": 0, "<NULL>": 0},
                    {"AU": 1, "EU": 1, "ID": 1, "US": 0, "<NULL>": 0},
                ],
            ), patch.object(
                mfa_runner,
                "import_report",
                return_value={
                    "mode": "dry_run",
                    "brands": [
                        {
                            "brand": "JS Industries",
                            "linked_model_rows": 4,
                            "linked_size_rows": 2,
                        }
                    ],
                },
            ), patch.object(
                mfa_runner,
                "build_brand",
                side_effect=lambda slug, **kwargs: {
                    "slug": slug,
                    "brand": mfa_runner.IMPLEMENTED_BRANDS[slug]["brandName"],
                    "source_status": "fresh",
                    "fresh_build_success": True,
                    "used_stale_fallback": False,
                    "rows_emitted": 5,
                    "error_type": None,
                    "error_message_summary": None,
                },
            ), patch.object(
                mfa_runner,
                "validate_output",
                side_effect=lambda slug: {
                    "brand": mfa_runner.IMPLEMENTED_BRANDS[slug]["brandName"],
                    "rows": 5,
                    "available_rows": 5,
                    "rows_with_dimensions": 5,
                    "output": f"{slug}.json",
                },
            ), patch.object(
                mfa_runner, "run"
            ) as run_command, patch(
                "sys.argv",
                ["run_us_manufacturer_availability_pipeline.py", "dry-run"],
            ), redirect_stdout(buffer):
                mfa_runner.main()
            self.assertTrue(report_path.exists())
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["regionCode"], "US")
            self.assertIn("Album", {brand["brandName"] for brand in payload["brands"]})
            self.assertEqual(payload["freshBrandCount"], len(mfa_runner.IMPLEMENTED_BRANDS))
            update_job_state.assert_called_once()
            self.assertEqual(run_command.call_args[0][0][-1], ",".join(target["brandName"] for target in mfa_runner.IMPLEMENTED_BRANDS.values()))

    def test_us_mfa_run_emits_heartbeat_and_completion(self):
        class FakeProcess:
            def __init__(self):
                self.returncode = 0
                self._poll_count = 0

            def poll(self):
                self._poll_count += 1
                if self._poll_count < 3:
                    return None
                return self.returncode

            def kill(self):
                self.returncode = -9

            def wait(self, timeout=None):
                return self.returncode

        fake_time_values = iter([0.0, 31.0, 31.0, 32.0, 32.0])
        buffer = StringIO()
        with patch.object(mfa_runner.subprocess, "Popen", return_value=FakeProcess()), patch.object(
            mfa_runner.time, "perf_counter", side_effect=lambda: next(fake_time_values)
        ), patch.object(mfa_runner.time, "sleep"), redirect_stdout(buffer):
            mfa_runner.run(
                ["python", "build.py"],
                timeout_seconds=120,
                progress_label="build:Album",
            )
        output = buffer.getvalue()
        self.assertIn("Command still running [build:Album] after 31.0s", output)
        self.assertIn("Command completed [build:Album] in 32.0s", output)

    def test_us_mfa_run_raises_command_timeout(self):
        class FakeProcess:
            def __init__(self):
                self.returncode = None
                self.killed = False

            def poll(self):
                return None

            def kill(self):
                self.killed = True

            def wait(self, timeout=None):
                return 1

        fake_process = FakeProcess()
        fake_time_values = iter([0.0, 61.0])
        with patch.object(mfa_runner.subprocess, "Popen", return_value=fake_process), patch.object(
            mfa_runner.time, "perf_counter", side_effect=lambda: next(fake_time_values)
        ), patch.object(mfa_runner.time, "sleep"):
            with self.assertRaisesRegex(mfa_runner.CommandTimeoutError, "timed out"):
                mfa_runner.run(
                    ["python", "build.py"],
                    timeout_seconds=60,
                    progress_label="build:Album",
                )
        self.assertTrue(fake_process.killed)

    def test_us_mfa_dry_run_skips_stale_brand_from_import(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "us_mfa_rollout_plan.json"
            with patch.object(mfa_runner, "emit_event") as emit_event, patch.object(
                mfa_runner, "update_job_state"
            ), patch.object(
                mfa_runner, "assert_region_scope"
            ), patch.object(
                mfa_runner, "REPORT_OUTPUT", report_path
            ), patch.object(
                mfa_runner,
                "region_counts",
                side_effect=[
                    {"AU": 1, "EU": 1, "ID": 1, "US": 10, "<NULL>": 0},
                    {"AU": 1, "EU": 1, "ID": 1, "US": 10, "<NULL>": 0},
                ],
            ), patch.object(
                mfa_runner,
                "build_brand",
                side_effect=lambda slug, **kwargs: {
                    "slug": slug,
                    "brand": mfa_runner.IMPLEMENTED_BRANDS[slug]["brandName"],
                    "source_status": "stale_fallback" if slug == "js_industries" else "fresh",
                    "fresh_build_success": slug != "js_industries",
                    "used_stale_fallback": slug == "js_industries",
                    "rows_emitted": 7,
                    "error_type": "SourceThrottleError" if slug == "js_industries" else None,
                    "error_message_summary": "HTTP 429" if slug == "js_industries" else None,
                },
            ), patch.object(
                mfa_runner,
                "validate_output",
                side_effect=lambda slug: {
                    "brand": mfa_runner.IMPLEMENTED_BRANDS[slug]["brandName"],
                    "rows": 7,
                    "available_rows": 7,
                    "rows_with_dimensions": 7,
                    "output": f"{slug}.json",
                },
            ), patch.object(
                mfa_runner,
                "import_report",
                return_value={"mode": "dry_run", "brands": []},
            ), patch.object(
                mfa_runner, "run"
            ) as run_command, patch(
                "sys.argv",
                ["run_us_manufacturer_availability_pipeline.py", "dry-run"],
            ):
                mfa_runner.main()
            import_brands = run_command.call_args[0][0][-1]
            self.assertNotIn("JS Industries", import_brands)
            self.assertIn("Channel Islands", import_brands)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            js_brand = next(item for item in payload["brands"] if item["brandName"] == "JS Industries")
            self.assertEqual(js_brand["source_status"], "stale_fallback")
            self.assertTrue(js_brand["used_stale_fallback"])
            self.assertFalse(js_brand["fresh_build_success"])

    def test_us_mfa_build_brand_degrades_cleanly_on_timeout(self):
        with patch.object(mfa_runner, "run", side_effect=mfa_runner.CommandTimeoutError("timeout")), patch.object(
            mfa_runner, "emit_event"
        ) as emit_event, patch.object(mfa_runner.time, "perf_counter", side_effect=[0.0, 5.0]):
            diagnostic = mfa_runner.build_brand("album", position=1, total=13)
        self.assertEqual(diagnostic["source_status"], "command_timeout")
        self.assertFalse(diagnostic["fresh_build_success"])
        self.assertEqual(diagnostic["rows_emitted"], 0)
        degraded_events = [call for call in emit_event.call_args_list if call.args[0] == "mfa_brand_degraded"]
        self.assertTrue(degraded_events)

    def test_us_manufacturer_plan_covers_requested_sources(self):
        payload = json.loads(
            (
                ROOT
                / "scrapers/manufacturers/availability/config/us_manufacturer_availability_targets.example.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(payload["regionCode"], "US")
        self.assertFalse(payload["enabled"])
        lost_target = next(target for target in payload["targets"] if target["brandName"] == "Lost")
        self.assertFalse(lost_target["enabled"])
        self.assertEqual(
            lost_target["builderStrategy"], "not_mfa_eligible_catalogue_plus_dealer_referrals"
        )
        self.assertEqual(
            {target["brandName"] for target in payload["targets"]},
            {
                *(target["brandName"] for target in mfa_runner.IMPLEMENTED_BRANDS.values()),
                *mfa_runner.SKIPPED_BRANDS.keys(),
            },
        )

    def test_us_mfa_importer_conforms_schema_bound_text_fields(self):
        conformed, truncations = us_mfa_importer.conform_payload_for_schema(
            {
                "Construction": "X" * 120,
                "FinSetup": "Y" * 140,
                "RawProductTitle": "Z" * 520,
                "SourcePayload": "P" * 2000,
                "PriceAmount": "799.999",
                "VolumeLitres": "31.555",
            },
            {
                "Construction",
                "FinSetup",
                "RawProductTitle",
                "SourcePayload",
                "PriceAmount",
                "VolumeLitres",
            },
        )
        self.assertEqual(len(conformed["Construction"]), 100)
        self.assertEqual(len(conformed["FinSetup"]), 100)
        self.assertEqual(len(conformed["RawProductTitle"]), 500)
        self.assertEqual(len(conformed["SourcePayload"]), 2000)
        self.assertEqual(conformed["PriceAmount"], 800.0)
        self.assertEqual(conformed["VolumeLitres"], 31.56)
        self.assertEqual(truncations["Construction"], 1)
        self.assertEqual(truncations["FinSetup"], 1)
        self.assertEqual(truncations["RawProductTitle"], 1)

    def test_us_mfa_importer_allows_non_usd_price_when_currency_is_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "pukas.json"
            payload_path.write_text(
                json.dumps(
                    [
                        {
                            "brandName": "Pukas",
                            "modelName": "Lotus",
                            "regionCode": "US",
                            "availabilitySource": "manufacturer_direct",
                            "priceAmount": 875.0,
                            "priceCurrency": "EUR",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(us_mfa_importer.FILES, {"Pukas": payload_path}, clear=True):
                rows = us_mfa_importer.load_rows({"Pukas"})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["priceCurrency"], "EUR")

    def test_us_mfa_importer_rejects_priced_rows_without_currency(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "broken.json"
            payload_path.write_text(
                json.dumps(
                    [
                        {
                            "brandName": "Pukas",
                            "modelName": "Lotus",
                            "regionCode": "US",
                            "availabilitySource": "manufacturer_direct",
                            "priceAmount": 875.0,
                            "priceCurrency": "",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(us_mfa_importer.FILES, {"Pukas": payload_path}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "priceCurrency"):
                    us_mfa_importer.load_rows({"Pukas"})

    def test_channel_islands_parser_extracts_schema_safe_fields(self):
        rows = us_mfa_builder.parse_ci_product(
            {
                "vendor": "Channel Islands Surfboards",
                "product_type": "Surfboards",
                "title": "6'2 Better Everyday - FCSII",
                "handle": "62-better-everyday-fcsii",
                "body_html": """
                    6'2 Better Everyday - FCSII
                    6'2 x 20 5/8 x 2 3/4
                    Volume: 37.3L
                    FCSII five fin set-up, fins not included
                    ECT-Carbon construction
                    Extra descriptive copy that should stay in SourcePayload.
                """,
                "variants": [
                    {"id": 1, "price": "850.00", "available": True, "title": "Default Title"}
                ],
                "images": [{"src": "https://example.com/board.jpg"}],
            },
            "2026-06-25T00:00:00Z",
            "https://cisurfboards.com",
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["thickness"], "2 3/4")
        self.assertEqual(row["finSetup"], "FCS II")
        self.assertEqual(row["construction"], "ECT-Carbon")
        self.assertLessEqual(len(row["finSetup"]), 100)
        self.assertLessEqual(len(row["construction"]), 100)

    def test_album_parser_extracts_dimensions_from_product_page(self):
        html = """
            <html>
              <body>
                <div class="lightly-spaced-row not-in-quickbuy">5'10" x 20" x 2.44" (33.4 Liters)</div>
              </body>
            </html>
        """
        with patch.object(us_mfa_builder.requests, "get", return_value=Mock(status_code=200, text=html, raise_for_status=Mock())):
            rows = us_mfa_builder.parse_album_product(
                {
                    "title": "5'10\" Twinzman (Exo Flex)",
                    "product_type": "Surfboard",
                    "handle": "510-twinzman-exo-flex",
                    "body_html": "<p>Fast hybrid twinzer.</p>",
                    "variants": [
                        {
                            "id": 123,
                            "title": "Twinzman",
                            "price": "1299.00",
                            "available": True,
                        }
                    ],
                    "images": [{"src": "https://example.com/twinzman.jpg"}],
                },
                "2026-06-25T00:00:00Z",
                "https://albumsurf.com",
                us_mfa_builder.extract_album_dimensions("https://albumsurf.com/products/510-twinzman-exo-flex?variant=123"),
            )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["brandName"], "Album")
        self.assertEqual(row["modelName"], "Twinzman")
        self.assertEqual(row["lengthFeetInches"], "5'10")
        self.assertEqual(row["width"], "20")
        self.assertEqual(row["thickness"], "2.44")
        self.assertEqual(row["volumeLitres"], 33.4)
        self.assertEqual(row["construction"], "Exo Flex")
        self.assertEqual(row["regionCode"], "US")

    def test_builder_uses_stale_output_when_source_is_throttled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            stale_path = output_root / "js_industries" / "output" / "js_industries_us_manufacturer_inventory.json"
            stale_path.parent.mkdir(parents=True, exist_ok=True)
            stale_path.write_text(
                json.dumps(
                    [
                        {
                            "brandName": "JS Industries",
                            "availabilitySource": "manufacturer_direct",
                            "regionCode": "US",
                            "priceCurrency": "USD",
                            "isAvailable": True,
                            "lengthFeetInches": "6'0",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with patch.object(us_mfa_builder, "OUTPUT_ROOT", output_root), patch.object(
                us_mfa_builder, "build_fresh", side_effect=us_mfa_builder.SourceThrottleError("HTTP 429")
            ):
                result = us_mfa_builder.build("js_industries")
            self.assertEqual(result["source_status"], "stale_fallback")
            self.assertTrue(result["used_stale_fallback"])
            self.assertFalse(result["fresh_build_success"])
            self.assertEqual(result["rows_emitted"], 1)
            self.assertEqual(result["error_type"], "SourceThrottleError")

    def test_pukas_builder_extracts_model_and_dimensions_from_title(self):
        with patch.object(
            us_mfa_additional,
            "fetch_shopify_products",
            return_value=[
                {
                    "id": 1,
                    "title": 'Pukas Surfboards - Lotus by David Santos - 6\'4" x 20.38" x 2.68" - 37.40L - DS02255',
                    "handle": "lotus-ds02255",
                    "product_type": "SURFBOARDS",
                    "variants": [{"id": 11, "price": "875.00", "available": True, "title": "Default Title"}],
                    "images": [{"src": "https://example.com/pukas.jpg"}],
                }
            ],
        ):
            rows = us_mfa_additional.build_pukas_rows(Mock())
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["brandName"], "Pukas")
        self.assertEqual(row["modelName"], "Lotus")
        self.assertEqual(row["lengthFeetInches"], "6'4")
        self.assertEqual(row["width"], "20.38")
        self.assertEqual(row["thickness"], "2.68")
        self.assertEqual(row["volumeLitres"], 37.4)
        self.assertEqual(row["priceCurrency"], "EUR")
        self.assertEqual(row["regionCode"], "US")

    def test_christenson_builder_parses_stock_listing_and_detail_page(self):
        listing_html = """
            <a href="/surfboard-stock/64-carrera-black-rails" class="product" data-item-id="1">
              <img data-image="https://example.com/carrera.jpg" />
              <div class="product-title">6'4 Carrera</div>
              <div class="product-price">$955.50</div>
            </a>
        """
        detail_html = """
            <html>
              <head>
                <title>6&#39;4 Carrera &mdash; Christenson surfboards</title>
                <meta property="og:description" content="6’4× 19 7/8 x 2 9/16 - 31.7L 5 x Futures - Black Rail Spray   All sales are final." />
                <meta property="product:price:amount" content="955.50" />
              </head>
            </html>
        """

        def fake_request(url):
            if url == us_mfa_additional.CHRISTENSON_STOCK_URL:
                return Mock(text=listing_html)
            if "64-carrera-black-rails" in url:
                return Mock(text=detail_html)
            raise AssertionError(url)

        rows = us_mfa_additional.build_christenson_rows(fake_request)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["brandName"], "Christenson")
        self.assertEqual(row["modelName"], "Carrera")
        self.assertEqual(row["lengthFeetInches"], "6'4")
        self.assertEqual(row["width"], "19 7/8")
        self.assertEqual(row["thickness"], "2 9/16")
        self.assertEqual(row["volumeLitres"], 31.7)
        self.assertEqual(row["finSetup"], "Futures")
        self.assertEqual(row["priceCurrency"], "USD")

    def test_shipping_metadata_mapping_flags_cross_region_us_sources(self):
        pukas = shipping_metadata_for_brand("Pukas", "US")
        christenson = shipping_metadata_for_brand("Christenson", "US")
        eu = shipping_metadata_for_brand("Pukas", "EU")
        self.assertEqual(pukas["sourceRegionCode"], "EU")
        self.assertEqual(pukas["shippingScope"], "worldwide")
        self.assertIn("ship from another region", pukas["shippingNote"])
        self.assertEqual(christenson["shippingScope"], "domestic_us")
        self.assertEqual(eu, {})


if __name__ == "__main__":
    unittest.main()
