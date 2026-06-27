import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from observability.operations_dashboard import _build_job_contracts
from scripts import run_all_brand_catalogues


ROOT = Path(__file__).resolve().parents[1]


class JobContractGuardrailsTests(unittest.TestCase):
    def test_all_configured_jobs_declare_contract_metadata(self):
        payload = json.loads((ROOT / "config" / "azure_container_jobs.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["jobs"])
        for job in payload["jobs"]:
            self.assertTrue(job.get("entryScript"), f"Missing entryScript for {job.get('jobName')}")
            self.assertTrue(job.get("readsTables"), f"Missing readsTables for {job.get('jobName')}")
            self.assertTrue(job.get("writesTables"), f"Missing writesTables for {job.get('jobName')}")
            self.assertTrue(job.get("writesFields"), f"Missing writesFields for {job.get('jobName')}")
            self.assertTrue(job.get("expectedSourceOutputs"), f"Missing expectedSourceOutputs for {job.get('jobName')}")

    def test_weekly_catalogue_runner_no_longer_invokes_manufacturer_availability(self):
        source = (ROOT / "scripts" / "run_all_brand_catalogues.py").read_text(encoding="utf-8")
        self.assertNotIn("run_au_manufacturer_availability_pipeline.py", source)

    def test_non_canonical_importers_do_not_create_board_models_or_sizes(self):
        disallowed_patterns = (
            "INSERT INTO dbo.BoardModels",
            "UPDATE dbo.BoardModels",
            "INSERT INTO dbo.BoardSizes",
            "UPDATE dbo.BoardSizes",
        )
        importer_paths = [
            ROOT / "scripts" / "import_retailer_inventory.py",
            ROOT / "scripts" / "import_slimes_newcastle_inventory.py",
            ROOT / "scripts" / "europe" / "import_eu_retailer_inventory.py",
            ROOT / "scripts" / "usa" / "import_us_retailer_inventory.py",
            ROOT / "scrapers" / "retailers" / "indonesia" / "import_indonesia_retailer_inventory.py",
            ROOT / "scripts" / "manufacturer_availability" / "import_eu_manufacturer_availability.py",
            ROOT / "scripts" / "manufacturer_availability" / "import_js_id_availability.py",
        ]
        for path in importer_paths:
            source = path.read_text(encoding="utf-8")
            for pattern in disallowed_patterns:
                self.assertNotIn(pattern, source, f"{path} should not mutate canonical tables")

    def test_weekly_catalogue_runner_continues_after_one_brand_failure(self):
        with TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "weekly_brand_catalogue_report.json"
            steps = [
                {"name": "Broken Brand", "command": ["python", "broken.py"]},
                {"name": "Healthy Brand", "command": ["python", "healthy.py"]},
                {"name": "Healthy Brand Two", "command": ["python", "healthy_two.py"]},
            ]
            events = []

            def record_event(*args, **kwargs):
                events.append((args, kwargs))

            with patch.object(run_all_brand_catalogues, "STEPS", steps), patch.object(
                run_all_brand_catalogues, "REPORT_PATH", report_path
            ), patch.object(
                run_all_brand_catalogues, "emit_event", side_effect=record_event
            ), patch.object(
                run_all_brand_catalogues, "update_job_state"
            ), patch.object(
                run_all_brand_catalogues,
                "run_step",
                side_effect=[
                    RuntimeError("broken"),
                    {
                        "brand": "Healthy Brand",
                        "status": "succeeded",
                        "command": "python healthy.py",
                        "pipeline_path": "healthy.py",
                        "return_code": 0,
                        "duration_seconds": 1.0,
                    },
                    {
                        "brand": "Healthy Brand Two",
                        "status": "succeeded",
                        "command": "python healthy_two.py",
                        "pipeline_path": "healthy_two.py",
                        "return_code": 0,
                        "duration_seconds": 1.0,
                    },
                ],
            ):
                with self.assertRaises(SystemExit) as raised:
                    run_all_brand_catalogues.main()

            self.assertEqual(raised.exception.code, 1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["failed_brands"], ["Broken Brand"])
            self.assertIn("Healthy Brand", report["succeeded_brands"])
            self.assertIn("Healthy Brand Two", report["succeeded_brands"])
            completed_brands = [
                kwargs.get("brand")
                for _args, kwargs in events
                if _args and _args[0] == "catalogue_brand_completed"
            ]
            self.assertIn("Healthy Brand", completed_brands)
            self.assertIn("Healthy Brand Two", completed_brands)
            failed_event = next(
                kwargs
                for _args, kwargs in events
                if _args and _args[0] == "catalogue_brand_failed"
            )
            self.assertEqual(failed_event["brand"], "Broken Brand")
            self.assertIn("traceback", failed_event)
            self.assertIn("error_message", failed_event)
            self.assertEqual(failed_event["command"], "python broken.py")

    def test_job_contract_matrix_flags_planning_only_us_mfa_runner(self):
        _, by_region = _build_job_contracts(
            ["AU", "EU", "ID", "US"],
            {
                "AU": {"jobs": []},
                "EU": {"jobs": []},
                "ID": {"jobs": []},
                "US": {"jobs": [{"jobName": "quivrr-us-mfr-availability", "region": "US", "status": "green", "statusReason": "placeholder"}]},
            },
        )
        us_mfa = next(row for row in by_region["US"] if row["jobName"] == "quivrr-us-mfr-availability")
        self.assertEqual(us_mfa["contractStatus"], "red")
        self.assertEqual(us_mfa["contractLabel"], "planning_only")


if __name__ == "__main__":
    unittest.main()
