import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as backend_app


class OperationsDashboardApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.cache_file = Path(self.temp_dir.name) / "ops_dashboard_cache.json"
        self.bootstrap_file = Path(self.temp_dir.name) / "ops_dashboard_bootstrap.json"
        self.lock_file = Path(self.temp_dir.name) / "ops_dashboard_cache.lock"
        backend_app.OPS_DASHBOARD_CACHE_FILE = self.cache_file
        backend_app.OPS_DASHBOARD_BOOTSTRAP_FILE = self.bootstrap_file
        backend_app.OPS_DASHBOARD_REFRESH_LOCK_FILE = self.lock_file
        backend_app.OPS_DASHBOARD_PREWARM_ON_STARTUP = False
        backend_app.OPS_DASHBOARD_ALLOW_SYNC_BUILD = False
        backend_app._ops_dashboard_cache["generated_at"] = 0.0
        backend_app._ops_dashboard_cache["payload"] = None
        backend_app._ops_dashboard_cache["loaded_from_disk"] = False
        backend_app._ops_dashboard_cache["refresh_in_progress"] = False
        self.client = TestClient(backend_app.app)

    def tearDown(self):
        backend_app._ops_dashboard_cache["generated_at"] = 0.0
        backend_app._ops_dashboard_cache["payload"] = None
        backend_app._ops_dashboard_cache["loaded_from_disk"] = False
        backend_app._ops_dashboard_cache["refresh_in_progress"] = False
        self.temp_dir.cleanup()

    def test_ops_dashboard_requires_key(self):
        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", "secret-key"):
            response = self.client.get("/api/ops/dashboard")

        self.assertEqual(response.status_code, 403)

    def test_ops_dashboard_returns_503_when_server_key_not_configured(self):
        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", ""):
            response = self.client.get("/api/ops/dashboard")

        self.assertEqual(response.status_code, 503)

    def test_ops_dashboard_returns_metrics_with_authorization_header(self):
        payload = {
            "generatedAtUtc": "2026-06-26T00:00:00Z",
            "version": backend_app.DASHBOARD_VERSION,
            "regions": ["AU", "EU", "ID", "US"],
            "regionOverview": [],
            "mfaHealth": [],
            "retailerHealth": [],
            "retailerHealthByRegion": {"AU": {"summary": {}, "retailers": []}},
            "jobHealth": [{"region": "AU", "jobName": "quivrr-nightly-au-inventory"}],
            "jobHealthByRegion": {"AU": {"summary": {"configuredJobs": 1}, "jobs": [{"jobName": "quivrr-nightly-au-inventory"}]}},
            "inventoryCounts": [],
            "linkQuality": {},
            "coverageGaps": [],
            "alerts": [{"severity": "red"}],
            "alertSummary": {"summary": {"critical": 1}},
            "regionDetails": {"AU": {}},
        }

        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", "secret-key"), patch.object(
            backend_app,
            "OPS_DASHBOARD_ALLOW_SYNC_BUILD",
            True,
        ), patch.object(
            backend_app,
            "build_operations_dashboard_metrics",
            return_value=payload,
        ):
            response = self.client.get(
                "/api/ops/dashboard",
                headers={"Authorization": "Bearer secret-key"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["version"], backend_app.DASHBOARD_VERSION)
        self.assertEqual(body["cacheStatus"], "miss")
        self.assertEqual(body["regions"], ["AU", "EU", "ID", "US"])
        self.assertIn("mfaHealth", body)
        self.assertIn("retailerHealth", body)
        self.assertIn("retailerHealthByRegion", body)
        self.assertIn("jobHealth", body)
        self.assertIn("jobHealthByRegion", body)
        self.assertIn("inventoryCounts", body)
        self.assertIn("linkQuality", body)
        self.assertIn("coverageGaps", body)
        self.assertIn("alerts", body)
        self.assertIn("alertSummary", body)
        self.assertIn("regionDetails", body)

    def test_ops_dashboard_cache_hits_after_first_request(self):
        payload = {
            "generatedAtUtc": "2026-06-26T00:00:00Z",
            "version": backend_app.DASHBOARD_VERSION,
            "regions": ["AU"],
            "regionOverview": [],
            "mfaHealth": [],
            "retailerHealth": [],
            "retailerHealthByRegion": {"AU": {"summary": {}, "retailers": []}},
            "jobHealth": [],
            "jobHealthByRegion": {"AU": {"summary": {"configuredJobs": 0}, "jobs": []}},
            "inventoryCounts": [],
            "linkQuality": {},
            "coverageGaps": [],
            "alerts": [],
            "alertSummary": {"summary": {"critical": 0}},
            "regionDetails": {"AU": {}},
        }

        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", "secret-key"), patch.object(
            backend_app,
            "OPS_DASHBOARD_ALLOW_SYNC_BUILD",
            True,
        ), patch.object(
            backend_app,
            "build_operations_dashboard_metrics",
            return_value=payload,
        ) as builder:
            first_response = self.client.get(
                "/api/ops/dashboard",
                headers={"x-ops-dashboard-key": "secret-key"},
            )
            second_response = self.client.get(
                "/api/ops/dashboard",
                headers={"x-ops-dashboard-key": "secret-key"},
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(first_response.json()["cacheStatus"], "miss")
        self.assertEqual(second_response.json()["cacheStatus"], "hit")
        self.assertEqual(builder.call_count, 1)

    def test_ops_dashboard_cold_miss_returns_warming_payload_without_sync_build(self):
        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", "secret-key"), patch.object(
            backend_app,
            "_start_ops_dashboard_refresh_locked",
            return_value=True,
        ) as refresh_starter, patch.object(
            backend_app,
            "build_operations_dashboard_metrics",
        ) as builder:
            response = self.client.get(
                "/api/ops/dashboard",
                headers={"x-ops-dashboard-key": "secret-key"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["cacheStatus"], "warming")
        self.assertTrue(body["warmingUp"])
        self.assertEqual(body["regions"], ["AU", "EU", "ID", "US"])
        self.assertEqual(refresh_starter.call_count, 1)
        builder.assert_not_called()

    def test_ops_dashboard_serves_stale_cache_while_refreshing(self):
        payload = {
            "generatedAtUtc": "2026-06-26T00:00:00Z",
            "version": backend_app.DASHBOARD_VERSION,
            "regions": ["AU"],
            "regionOverview": [],
            "mfaHealth": [],
            "retailerHealth": [],
            "retailerHealthByRegion": {"AU": {"summary": {}, "retailers": []}},
            "jobHealth": [],
            "jobHealthByRegion": {"AU": {"summary": {"configuredJobs": 0}, "jobs": []}},
            "inventoryCounts": [],
            "linkQuality": {},
            "coverageGaps": [],
            "alerts": [],
            "alertSummary": {"summary": {"critical": 0}},
            "regionDetails": {"AU": {}},
        }
        backend_app._ops_dashboard_cache["generated_at"] = 1.0
        backend_app._ops_dashboard_cache["payload"] = dict(payload)
        backend_app._ops_dashboard_cache["loaded_from_disk"] = True

        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", "secret-key"), patch.object(
            backend_app,
            "OPS_DASHBOARD_CACHE_TTL_SECONDS",
            1,
        ), patch.object(
            backend_app,
            "_start_ops_dashboard_refresh_locked",
            return_value=True,
        ) as refresh_starter, patch.object(
            backend_app,
            "build_operations_dashboard_metrics",
        ) as builder:
            response = self.client.get(
                "/api/ops/dashboard",
                headers={"x-ops-dashboard-key": "secret-key"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cacheStatus"], "stale")
        self.assertEqual(refresh_starter.call_count, 1)
        builder.assert_not_called()

    def test_ops_dashboard_loads_cached_snapshot_from_disk(self):
        payload = {
            "generatedAtUtc": "2026-06-26T00:00:00Z",
            "version": backend_app.DASHBOARD_VERSION,
            "regions": ["AU"],
            "regionOverview": [],
            "mfaHealth": [],
            "retailerHealth": [],
            "retailerHealthByRegion": {"AU": {"summary": {}, "retailers": []}},
            "jobHealth": [],
            "jobHealthByRegion": {"AU": {"summary": {"configuredJobs": 0}, "jobs": []}},
            "inventoryCounts": [],
            "linkQuality": {},
            "coverageGaps": [],
            "alerts": [],
            "alertSummary": {"summary": {"critical": 0}},
            "regionDetails": {"AU": {}},
        }
        self.cache_file.write_text(
            '{"generated_at": ' + str(time.time()) + ', "payload": {"generatedAtUtc": "2026-06-26T00:00:00Z", "version": "' + backend_app.DASHBOARD_VERSION + '", "regions": ["AU"], "regionOverview": [], "mfaHealth": [], "retailerHealth": [], "retailerHealthByRegion": {"AU": {"summary": {}, "retailers": []}}, "jobHealth": [], "jobHealthByRegion": {"AU": {"summary": {"configuredJobs": 0}, "jobs": []}}, "inventoryCounts": [], "linkQuality": {}, "coverageGaps": [], "alerts": [], "alertSummary": {"summary": {"critical": 0}}, "regionDetails": {"AU": {}}}}',
            encoding="utf-8",
        )

        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", "secret-key"), patch.object(
            backend_app,
            "OPS_DASHBOARD_CACHE_TTL_SECONDS",
            3600,
        ), patch.object(
            backend_app,
            "build_operations_dashboard_metrics",
        ) as builder:
            response = self.client.get(
                "/api/ops/dashboard",
                headers={"x-ops-dashboard-key": "secret-key"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cacheStatus"], "hit")
        self.assertEqual(response.json()["version"], payload["version"])
        builder.assert_not_called()

    def test_ops_dashboard_loads_bootstrap_snapshot_when_runtime_cache_missing(self):
        payload = {
            "generatedAtUtc": "2026-06-26T00:00:00Z",
            "version": backend_app.DASHBOARD_VERSION,
            "regions": ["AU"],
            "regionOverview": [],
            "mfaHealth": [],
            "retailerHealth": [],
            "retailerHealthByRegion": {"AU": {"summary": {}, "retailers": []}},
            "jobHealth": [],
            "jobHealthByRegion": {"AU": {"summary": {"configuredJobs": 0}, "jobs": []}},
            "inventoryCounts": [],
            "linkQuality": {},
            "coverageGaps": [],
            "alerts": [],
            "alertSummary": {"summary": {"critical": 0}},
            "regionDetails": {"AU": {}},
        }
        self.bootstrap_file.write_text(
            '{"generated_at": ' + str(time.time()) + ', "payload": {"generatedAtUtc": "2026-06-26T00:00:00Z", "version": "' + backend_app.DASHBOARD_VERSION + '", "regions": ["AU"], "regionOverview": [], "mfaHealth": [], "retailerHealth": [], "retailerHealthByRegion": {"AU": {"summary": {}, "retailers": []}}, "jobHealth": [], "jobHealthByRegion": {"AU": {"summary": {"configuredJobs": 0}, "jobs": []}}, "inventoryCounts": [], "linkQuality": {}, "coverageGaps": [], "alerts": [], "alertSummary": {"summary": {"critical": 0}}, "regionDetails": {"AU": {}}}}',
            encoding="utf-8",
        )

        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", "secret-key"), patch.object(
            backend_app,
            "OPS_DASHBOARD_CACHE_TTL_SECONDS",
            3600,
        ), patch.object(
            backend_app,
            "build_operations_dashboard_metrics",
        ) as builder:
            response = self.client.get(
                "/api/ops/dashboard",
                headers={"x-ops-dashboard-key": "secret-key"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cacheStatus"], "hit")
        self.assertEqual(response.json()["version"], payload["version"])
        builder.assert_not_called()

    def test_ops_dashboard_ignores_cached_snapshot_with_old_version(self):
        self.cache_file.write_text(
            '{"generated_at": ' + str(time.time()) + ', "payload": {"generatedAtUtc": "2026-06-26T00:00:00Z", "version": "stale-dashboard-version", "regions": ["AU"], "regionOverview": [], "mfaHealth": [], "retailerHealth": [], "retailerHealthByRegion": {"AU": {"summary": {}, "retailers": []}}, "jobHealth": [], "jobHealthByRegion": {"AU": {"summary": {"configuredJobs": 0}, "jobs": []}}, "inventoryCounts": [], "linkQuality": {}, "coverageGaps": [], "alerts": [], "alertSummary": {"summary": {"critical": 0}}, "regionDetails": {"AU": {}}}}',
            encoding="utf-8",
        )

        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", "secret-key"), patch.object(
            backend_app,
            "_start_ops_dashboard_refresh_locked",
            return_value=True,
        ) as refresh_starter, patch.object(
            backend_app,
            "build_operations_dashboard_metrics",
        ) as builder:
            response = self.client.get(
                "/api/ops/dashboard",
                headers={"x-ops-dashboard-key": "secret-key"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cacheStatus"], "warming")
        self.assertTrue(response.json()["warmingUp"])
        self.assertEqual(refresh_starter.call_count, 1)
        builder.assert_not_called()

    def test_ops_dashboard_ignores_bootstrap_snapshot_with_old_version(self):
        self.bootstrap_file.write_text(
            '{"generated_at": ' + str(time.time()) + ', "payload": {"generatedAtUtc": "2026-06-26T00:00:00Z", "version": "stale-dashboard-version", "regions": ["AU"], "regionOverview": [], "mfaHealth": [], "retailerHealth": [], "retailerHealthByRegion": {"AU": {"summary": {}, "retailers": []}}, "jobHealth": [], "jobHealthByRegion": {"AU": {"summary": {"configuredJobs": 0}, "jobs": []}}, "inventoryCounts": [], "linkQuality": {}, "coverageGaps": [], "alerts": [], "alertSummary": {"summary": {"critical": 0}}, "regionDetails": {"AU": {}}}}',
            encoding="utf-8",
        )

        with patch.object(backend_app, "OPS_DASHBOARD_API_KEY", "secret-key"), patch.object(
            backend_app,
            "_start_ops_dashboard_refresh_locked",
            return_value=True,
        ) as refresh_starter, patch.object(
            backend_app,
            "build_operations_dashboard_metrics",
        ) as builder:
            response = self.client.get(
                "/api/ops/dashboard",
                headers={"x-ops-dashboard-key": "secret-key"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cacheStatus"], "warming")
        self.assertTrue(response.json()["warmingUp"])
        self.assertEqual(refresh_starter.call_count, 1)
        builder.assert_not_called()


if __name__ == "__main__":
    unittest.main()
