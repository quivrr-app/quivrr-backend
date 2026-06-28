import unittest
from pathlib import Path
from unittest.mock import patch

from audits import canonical_catalogue_health
from scripts import canonical_catalogue_guardrails as guardrails
from scripts.import_brand_catalogue_common import (
    build_rejected_model_cleanup_targets,
    validate_missing_model_deactivation,
)
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

    def test_rejected_model_cleanup_targets_are_deduplicated_and_keep_source_urls(self):
        targets = build_rejected_model_cleanup_targets(
            [
                {
                    "brand": "Album",
                    "title": "Aaron Poritz",
                    "sourceUrl": "https://albumsurf.com/collections/aaron-poritz",
                    "reason": "negative_term:vase",
                },
                {
                    "brand": "Album",
                    "title": "Aaron Poritz",
                    "sourceUrl": "https://albumsurf.com/collections/aaron-poritz",
                    "reason": "negative_term:vase",
                },
                {
                    "brand": "Album",
                    "title": "Gallery Tee",
                    "sourceUrl": "https://albumsurf.com/products/gallery-tee",
                    "reason": "negative_term:shirt",
                },
            ]
        )

        self.assertEqual(
            targets,
            [
                {
                    "model_name": "Aaron Poritz",
                    "source_url": "https://albumsurf.com/collections/aaron-poritz",
                    "reason": "negative_term:vase",
                },
                {
                    "model_name": "Gallery Tee",
                    "source_url": "https://albumsurf.com/products/gallery-tee",
                    "reason": "negative_term:shirt",
                },
            ],
        )

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

    def test_generic_importer_supports_script_directory_runtime_imports(self):
        generic_importer = Path("scripts/import_brand_catalogue_common.py").read_text(encoding="utf-8")
        self.assertIn("except ModuleNotFoundError", generic_importer)
        self.assertIn("from canonical_catalogue_guardrails import (", generic_importer)

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

    def test_album_aaron_poritz_vase_is_rejected(self):
        assessment = guardrails.assess_catalogue_candidate(
            brand="Album",
            title="Aaron Poritz Vase",
            source_url="https://albumsurf.com/collections/aaron-poritz-vase",
            board_category="Art",
            detected_product_type="Ceramic Vase",
            description="Album art vase collaboration.",
        )
        self.assertFalse(assessment["accepted"])
        self.assertIn("negative_term", assessment["reason"])

    def test_real_album_surfboard_with_dimensions_passes(self):
        assessment = guardrails.assess_catalogue_candidate(
            brand="Album",
            title="Bom Dia",
            source_url="https://albumsurf.com/collections/bom-dia",
            board_category="Surfboard",
            source_variant_title='5\'6 x 19 1/2 x 2 7/16 29.3L',
            length="5'6",
            width="19 1/2",
            thickness="2 7/16",
            volume_litres=29.3,
        )
        self.assertTrue(assessment["accepted"])
        self.assertEqual(assessment["reason"], "dimension_signal")

    def test_products_without_surfboard_evidence_are_rejected(self):
        accepted, rejected = guardrails.filter_catalogue_rows(
            "Album",
            [
                {
                    "model_name": "Ledge",
                    "board_category": None,
                    "official_product_url": "https://albumsurf.com/collections/ledge",
                    "source_product_title": "Ledge",
                    "source_variant_title": "Model overview",
                    "length_feet_inches": None,
                    "width": None,
                    "thickness": None,
                    "volume_litres": None,
                }
            ],
        )
        self.assertEqual(accepted, [])
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["reason"], "missing_surfboard_evidence")

    def test_model_only_album_page_with_surfboard_context_passes(self):
        accepted, rejected = guardrails.filter_catalogue_rows(
            "Album",
            [
                {
                    "model_name": "Ledge",
                    "board_category": None,
                    "official_product_url": "https://albumsurf.com/collections/ledge-1",
                    "source_product_title": "Ledge",
                    "source_variant_title": "Model overview",
                    "description": "New age step-up with modern rails and paddle power for critical surf.",
                    "length_feet_inches": None,
                    "width": None,
                    "thickness": None,
                    "volume_litres": None,
                }
            ],
        )
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected, [])

    def test_model_only_non_surfboard_collaboration_is_rejected(self):
        accepted, rejected = guardrails.filter_catalogue_rows(
            "Album",
            [
                {
                    "model_name": "Korua Album",
                    "board_category": None,
                    "official_product_url": "https://albumsurf.com/collections/korua-album",
                    "source_product_title": "Korua Album",
                    "source_variant_title": "Model overview",
                    "description": "Pencil // 147 and Cafe Racer // 164 sold out.",
                    "length_feet_inches": None,
                    "width": None,
                    "thickness": None,
                    "volume_litres": None,
                }
            ],
        )
        self.assertEqual(accepted, [])
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["reason"], "missing_surfboard_evidence")

    def test_supported_brands_keep_valid_dimension_rows(self):
        accepted, rejected = guardrails.filter_catalogue_rows(
            "JS Industries",
            [
                {
                    "model_name": "Golden Child",
                    "board_category": "Shortboard",
                    "official_product_url": "https://jsindustries.com/products/golden-child",
                    "source_variant_title": '5\'11 x 18 5/8 x 2 3/8 26.8L',
                    "length_feet_inches": "5'11",
                    "width": "18 5/8",
                    "thickness": "2 3/8",
                    "volume_litres": 26.8,
                },
                {
                    "model_name": "Happy Twin",
                    "board_category": "Twin Fin Surfboard",
                    "official_product_url": "https://pyzelsurfboards.com/products/happy-twin",
                    "source_variant_title": '5\'8 x 19 1/2 x 2 7/16 28.7L',
                    "length_feet_inches": "5'8",
                    "width": "19 1/2",
                    "thickness": "2 7/16",
                    "volume_litres": 28.7,
                },
            ],
        )
        self.assertEqual(len(accepted), 2)
        self.assertEqual(rejected, [])

    def test_dimensionless_rows_do_not_create_sizes(self):
        size_rows = [
            {
                "model_id": 1,
                "length": None,
                "width": None,
                "thickness": None,
                "volume": None,
                "construction": None,
                "fin_setup": None,
                "tail_shape": None,
            },
            {
                "model_id": 1,
                "length": "5'8",
                "width": "19 1/2",
                "thickness": "2 7/16",
                "volume": 29.3,
                "construction": "PU",
                "fin_setup": "FCS II",
                "tail_shape": "Squash",
            },
        ]
        filtered = [row for row in size_rows if row["length"]]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["length"], "5'8")
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
