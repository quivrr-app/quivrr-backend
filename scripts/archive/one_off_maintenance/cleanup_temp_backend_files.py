from pathlib import Path
from datetime import datetime
import shutil

root = Path(".")
archive = root / "_cleanup_archive" / datetime.now().strftime("%Y%m%d_%H%M%S")
archive.mkdir(parents=True, exist_ok=True)

root_temp_files = [
    "add_lost_to_weekly_brand_runner.py",
    "add_pyzel_dhd_brand_catalogues.py",
    "add_slimes_verbose_logging.py",
    "check_lost_quality.py",
    "check_pyzel_dhd_catalogue_quality.py",
    "check_pyzel_dhd_images_urls.py",
    "check_pyzel_eps_models_sql.py",
    "check_pyzel_eps_sql.py",
    "check_pyzel_model_constructions_json.py",
    "create_firewire_importer.py",
    "create_firewire_pipeline.py",
    "create_lost_importer.py",
    "create_lost_pipeline_runner.py",
    "create_rusty_importer.py",
    "create_rusty_pipeline.py",
    "deactivate_overboard_retailer.py",
    "debug_happy_everyday_search.py",
    "discover_retailer_schema.py",
    "fix_add_rusty_weekly.py",
    "fix_brand_pipeline_python_runtime.py",
    "fix_brand_runner_real_paths.py",
    "fix_dhd_current_models.py",
    "fix_dhd_eps_construction.py",
    "fix_dhd_models_and_construction.py",
    "fix_firewire_dimension_parser.py",
    "fix_firewire_fraction_split.py",
    "fix_firewire_parser.py",
    "fix_firewire_regex.py",
    "fix_firewire_skip_gift_card.py",
    "fix_lost_model_normalisation.py",
    "fix_preserve_source_product_title.py",
    "fix_pyzel_dhd_import_paths.py",
    "fix_pyzel_dhd_volume_and_names.py",
    "fix_pyzel_epoxy_detection.py",
    "fix_pyzel_eps_construction.py",
    "fix_pyzel_models_and_construction.py",
    "fix_pyzel_region_suffix_models.py",
    "fix_run_all_brand_catalogues_four_brands.py",
    "fix_rusty_length_normalisation.py",
    "fix_slimes_importer_dimensions.py",
    "inspect_pyzel_eps_source_rows.py",
    "interrogate_live_retailers.py",
    "interrogate_retailers_sql.py",
    "patch_firewire_extract_dimensions.py",
    "patch_firewire_segmented_parser.py",
    "probe_rusty_eu_variants.py",
    "probe_slimes_newcastle.py",
    "probe_surfection_mosman.py",
    "productionise_slimes_newcastle.py",
    "replace_firewire_builder.py",
    "replace_pyzel_cleaner_strict.py",
    "review_nightly_retailer_scrape.py",
    "rusty_quality_output.txt",
    "safe_fix_rusty_length_normalisation.py",
    "scrape_and_import_slimes_newcastle.py",
    "scrape_and_import_surfection_mosman.py",
    "script_patch_firewire_builder.py",
    "upgrade_firewire_regex.py",
    "verify_firewire_sql_import.py",
    "verify_pyzel_dhd_sql_import.py",
    "verify_rusty_sql_import.py",
    "verify_slimes_happy_everyday.py",
    "wire_firewire_into_weekly.py",
    "wire_rusty_into_weekly.py",
]

for item in root_temp_files:
    path = root / item
    if path.exists():
        shutil.move(str(path), str(archive / path.name))

for path in root.rglob("__pycache__"):
    shutil.rmtree(path, ignore_errors=True)

for path in root.rglob("*.pyc"):
    path.unlink(missing_ok=True)

print(f"Archived temporary files to: {archive}")
print("Runtime files preserved.")
