import inspect
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as backend_app
from auth import entra_external_id


class IdentityFoundationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(backend_app.app)

    def test_public_brands_endpoint_remains_unauthenticated(self):
        with patch.object(
            backend_app,
            "execute_with_retry",
            return_value=[SimpleNamespace(BrandId=1, BrandName="Album")],
        ):
            response = self.client.get("/api/brands")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{"brandId": 1, "brandName": "Album"}])

    def test_public_search_endpoint_has_no_authorization_parameter(self):
        signature = inspect.signature(backend_app.search_inventory)
        self.assertNotIn("authorization", signature.parameters)

    def test_auth_config_missing_does_not_break_app_startup(self):
        self.assertIsNotNone(backend_app.app)
        with patch.dict(os.environ, {value: "" for value in entra_external_id.ENTRA_CONFIG_KEYS.values()}):
            self.assertFalse(entra_external_id.is_configured())

    def test_protected_endpoint_returns_503_when_auth_is_not_configured(self):
        response = self.client.get("/api/me")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["provider"], "microsoft_entra_external_id")
        self.assertFalse(response.json()["detail"]["configured"])

    def test_protected_endpoint_rejects_invalid_or_missing_user(self):
        with patch.object(backend_app, "entra_auth_is_configured", return_value=True), patch.object(
            backend_app, "entra_missing_config_keys", return_value=[]
        ), patch.object(
            backend_app, "require_current_user", side_effect=backend_app.AuthValidationError("Authentication is required.")
        ):
            response = self.client.get("/api/me", headers={"Authorization": "Bearer bad-token"})

        self.assertEqual(response.status_code, 401)

    def test_events_endpoint_accepts_anonymous_payload(self):
        response = self.client.post(
            "/api/events",
            json={
                "anonymousSessionId": "anon-session-1",
                "eventType": "search_viewed",
                "regionCode": "AU",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "accepted_not_persisted")
        self.assertFalse(body["authenticated"])
        self.assertEqual(body["anonymousSessionId"], "anon-session-1")

    def test_jwt_validator_module_exports_expected_functions(self):
        self.assertTrue(callable(entra_external_id.get_jwks))
        self.assertTrue(callable(entra_external_id.validate_access_token))
        self.assertTrue(callable(entra_external_id.get_current_user_optional))
        self.assertTrue(callable(entra_external_id.require_current_user))

    def test_identity_sql_script_is_present(self):
        script = Path("sql/identity/001_create_my_quivrr_identity_tables.sql")
        self.assertTrue(script.exists())
        text = script.read_text(encoding="utf-8")
        for table_name in (
            "dbo.Users",
            "dbo.UserProfiles",
            "dbo.UserConsents",
            "dbo.UserEvents",
            "dbo.SavedBoards",
            "dbo.UserWatchlists",
            "dbo.UserNotificationSettings",
            "dbo.RecommendationHistory",
        ):
            self.assertIn(table_name, text)


if __name__ == "__main__":
    unittest.main()
