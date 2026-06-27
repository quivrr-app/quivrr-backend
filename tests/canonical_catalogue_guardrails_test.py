import unittest
from pathlib import Path
from unittest.mock import patch

from audits import canonical_catalogue_health
from scripts.import_brand_catalogue_common import validate_missing_model_deactivation
from scrapers.brands.channel_islands import build_ci_canonical_model_links


class CanonicalCatalogueGuardrailsTests(unittest.TestCase):
    def test_deactivation_guard_blocks_large_unreviewed_model_drop(self):
        with self.assertRaises(RuntimeError) as raised:
            validate_missing_model_deactivation(
                brand_name="JS Industries",
                existing_model_names=[
                    "Golden Child",
                    "Monsta",
                    "Raging Bull",
                    "Xero Gravity",
                    "Xero Fusion",
                    "Bull Run",
                    "Black Baron",
                    "Big Baron",
                ],
                incoming_model_names=["Golden Child", "Monsta"],
            )

        message = str(raised.exception)
        self.assertIn("blocked deactivation of 6 models", message)
        self.assertIn("Sample missing models: Big Baron, Black Baron, Bull Run", message)

    def test_deactivation_guard_allows_small_reviewable_cleanup(self):
        missing = validate_missing_model_deactivation(
            brand_name="Album",
            existing_model_names=["Bom Dia", "Moonstone", "Ledge"],
            incoming_model_names=["Bom Dia", "Moonstone"],
        )
        self.assertEqual(missing, ["Ledge"])

    def test_canonical_summary_includes_official_model_audit_fields(self):
        brand_entry = {"displayName": "Pyzel", "primaryBrandId": 2, "brandIds": [2]}
        with patch.object(
            canonical_catalogue_health,
            "_extract_source_models",
            return_value=["74", "Happy Twin"],
        ), patch.object(
            canonical_catalogue_health,
            "_extract_latest_build_timestamp",
            return_value="2026-06-27T00:00:00+00:00",
        ), patch.object(
            canonical_catalogue_health,
            "_source_report_summary",
            return_value={"exists": True, "models": 2},
        ):
            payload = canonical_catalogue_health.summarize_brand_health(
                brand_entry,
                [
                    {"BoardModelId": 10, "BrandId": 2, "ModelName": "Happy Twin", "ModelTimestamp": None},
                ],
                [
                    {"BoardModelId": 10, "BrandId": 2, "SizeCount": 3, "Construction": "PU"},
                ],
                ["Happy Twin"],
            )

        self.assertEqual(payload["officialModelCount"], 2)
        self.assertEqual(payload["officialModelsMissingFromCanonical"], ["74"])
        self.assertEqual(payload["latestWeeklyBuildUtc"], "2026-06-27T00:00:00+00:00")
        self.assertEqual(payload["modelsWithDescription"], 0)
        self.assertEqual(payload["descriptionCoveragePct"], 0.0)
        self.assertIn("official_models_missing:1", payload["suspiciousModelLossIndicators"])

    def test_catalogue_importers_preserve_existing_descriptions_when_scrape_is_partial(self):
        generic_importer = Path("scripts/import_brand_catalogue_common.py").read_text(encoding="utf-8")
        ci_importer = Path("scripts/import_ci_catalogue.py").read_text(encoding="utf-8")
        js_importer = Path("scripts/import_js_catalogue.py").read_text(encoding="utf-8")

        self.assertIn("Description = COALESCE(:description, Description)", generic_importer)
        self.assertIn("Description = COALESCE(:description, Description)", ci_importer)
        self.assertIn("Description = COALESCE(:description, Description)", js_importer)

    def test_ci_model_link_builder_rejects_junk_titles_and_template_slugs(self):
        self.assertFalse(build_ci_canonical_model_links.looks_like_model_title("Comments"))
        self.assertFalse(build_ci_canonical_model_links.looks_like_model_title("Videos"))
        self.assertFalse(build_ci_canonical_model_links.looks_like_model_title("{{ product.title }}"))
        self.assertFalse(build_ci_canonical_model_links.looks_like_model_slug("{{ product.handle }}"))
        self.assertTrue(build_ci_canonical_model_links.looks_like_model_title("M23"))
        self.assertTrue(build_ci_canonical_model_links.looks_like_model_slug("m23"))

    def test_ci_model_link_builder_detects_parent_model_products_in_shopify_feed(self):
        self.assertTrue(
            build_ci_canonical_model_links.looks_like_parent_model_product(
                {
                    "product_type": "Legacy Surfboard Model",
                    "title": "The Gravy",
                    "handle": "the-gravy",
                }
            )
        )
        self.assertFalse(
            build_ci_canonical_model_links.looks_like_parent_model_product(
                {
                    "product_type": "Surfboard Stock",
                    "title": "5'8 Two Happy - Futures",
                    "handle": "58-two-happy-futures",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
