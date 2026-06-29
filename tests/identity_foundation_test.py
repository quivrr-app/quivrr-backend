import inspect
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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

    def test_me_returns_persisted_identity_bundle(self):
        bundle = {
            "isNewUser": True,
            "user": {
                "UserId": "user-1",
                "EntraObjectId": "entra-1",
                "Email": "surfer@example.com",
                "DisplayName": "Test Surfer",
                "IdentityProvider": "google.com",
                "HomeRegion": "AU",
                "CreatedUtc": "2026-01-01T00:00:00",
                "LastLoginUtc": "2026-01-02T00:00:00",
            },
            "profile": {"Ability": None, "PreferredBrands": None, "UpdatedUtc": "2026-01-02T00:00:00"},
            "consent": {
                "ConsentVersion": "my-quivrr-consent-v1",
                "MarketingConsent": False,
                "AnalyticsConsent": False,
                "ProductNotificationConsent": False,
            },
        }

        with patch.object(backend_app, "resolve_persisted_identity_bundle", return_value=bundle):
            response = self.client.get("/api/me", headers={"Authorization": "Bearer token"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["authenticated"])
        self.assertTrue(body["isNewUser"])
        self.assertFalse(body["profileComplete"])
        self.assertEqual(body["profileStrength"], "none")
        self.assertEqual(body["profileUsefulFieldCount"], 1)
        self.assertEqual(body["user"]["entraObjectId"], "entra-1")
        self.assertEqual(body["consent"]["consentVersion"], "my-quivrr-consent-v1")

    def test_profile_update_persists_optional_fields(self):
        bundle = {
            "isNewUser": False,
            "user": {
                "UserId": "user-1",
                "EntraObjectId": "entra-1",
                "Email": "surfer@example.com",
                "DisplayName": "Test Surfer",
                "IdentityProvider": "entra_external_id",
                "HomeRegion": None,
                "CreatedUtc": None,
                "LastLoginUtc": None,
            },
            "profile": {},
            "consent": {},
        }
        updated_bundle = {
            **bundle,
            "profile": {
                "HeightCm": 180,
                "WeightKg": 78,
                "Ability": "Intermediate",
                "CurrentVolumeLitres": 30.0,
                "PreferredVolumeMinLitres": 28.0,
                "PreferredVolumeMaxLitres": 32.0,
                "WaveType": "Beach break",
                "WaveSize": None,
                "SurfFrequency": None,
                "PreferredBrands": '["Album"]',
                "CurrentBoard": "5'8 daily driver",
                "SurfingGoal": "More speed",
                "HomeBreak": "Manly",
                "HomeCountry": "Australia",
                "UpdatedUtc": None,
            },
        }
        fake_connection = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_connection
        fake_context.__exit__.return_value = None

        with patch.object(backend_app, "resolve_persisted_identity_bundle", return_value=bundle), patch.object(
            backend_app.engine, "begin", return_value=fake_context
        ), patch.object(backend_app, "fetch_identity_bundle", return_value=updated_bundle):
            response = self.client.put(
                "/api/my-quivrr/profile",
                headers={"Authorization": "Bearer token"},
                json={
                    "displayName": "Test Surfer",
                    "homeRegion": "AU",
                    "heightCm": "180",
                    "weightKg": 78,
                    "ability": "Intermediate",
                    "currentVolumeLitres": "30",
                    "preferredVolumeMinLitres": 28,
                    "preferredVolumeMaxLitres": 32,
                    "waveType": "Beach break",
                    "preferredBrands": ["Album"],
                    "currentBoard": "5'8 daily driver",
                    "surfingGoal": "More speed",
                    "homeBreak": "Manly",
                    "homeCountry": "Australia",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "saved")
        self.assertTrue(body["profileComplete"])
        self.assertEqual(body["profileStrength"], "strong")
        self.assertEqual(body["profile"]["heightCm"], 180)
        self.assertEqual(body["profile"]["preferredBrands"], ["Album"])
        self.assertEqual(body["profile"]["currentBoard"], "5'8 daily driver")
        self.assertGreaterEqual(fake_connection.execute.call_count, 3)

    def test_profile_update_preserves_omitted_values_and_allows_explicit_clears(self):
        bundle = {
            "isNewUser": False,
            "user": {
                "UserId": "user-1",
                "EntraObjectId": "entra-1",
                "Email": "surfer@example.com",
                "DisplayName": "Test Surfer",
                "IdentityProvider": "entra_external_id",
                "HomeRegion": "AU",
                "CreatedUtc": None,
                "LastLoginUtc": None,
            },
            "profile": {
                "HeightCm": 180,
                "WeightKg": 78,
                "Ability": "Intermediate",
                "CurrentVolumeLitres": 30.0,
                "PreferredVolumeMinLitres": 28.0,
                "PreferredVolumeMaxLitres": 32.0,
                "WaveType": "Beach break",
                "WaveSize": "2 to 3 ft",
                "SurfFrequency": "Weekly",
                "PreferredBrands": '["Album","Pyzel"]',
                "CurrentBoard": "Twin",
                "SurfingGoal": "More speed",
                "HomeBreak": "Manly",
                "HomeCountry": "Australia",
                "UpdatedUtc": None,
            },
            "consent": {},
        }
        updated_bundle = {
            **bundle,
            "profile": {
                **bundle["profile"],
                "CurrentBoard": None,
                "SurfingGoal": "More hold",
            },
        }
        fake_connection = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_connection
        fake_context.__exit__.return_value = None

        with patch.object(backend_app, "resolve_persisted_identity_bundle", return_value=bundle), patch.object(
            backend_app.engine, "begin", return_value=fake_context
        ), patch.object(backend_app, "fetch_identity_bundle", return_value=updated_bundle):
            response = self.client.put(
                "/api/my-quivrr/profile",
                headers={"Authorization": "Bearer token"},
                json={
                    "surfingGoal": "More hold",
                    "clearFields": ["currentBoard"],
                },
            )

        self.assertEqual(response.status_code, 200)
        params = fake_connection.execute.call_args_list[1].args[1]
        self.assertEqual(params["height_cm"], 180)
        self.assertEqual(params["preferred_brands"], '["Album","Pyzel"]')
        self.assertIsNone(params["current_board"])
        self.assertEqual(params["surfing_goal"], "More hold")

    def test_logout_is_stateless_client_session_acknowledgement(self):
        response = self.client.post("/api/logout")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_identity_user_creation_uses_entra_object_id_and_default_consent(self):
        class FakeRow:
            def __init__(self, mapping):
                self._mapping = mapping

        class FakeResult:
            def __init__(self, row=None):
                self.row = row

            def fetchone(self):
                return self.row

        fake_connection = MagicMock()
        fake_connection.execute.side_effect = [
            FakeResult(None),
            FakeResult(),
            FakeResult(),
            FakeResult(),
            FakeResult(FakeRow({
                "UserId": "user-1",
                "EntraObjectId": "entra-1",
                "Email": "surfer@example.com",
                "DisplayName": "Test Surfer",
                "IdentityProvider": "microsoft",
                "HomeRegion": None,
                "CreatedUtc": None,
                "LastLoginUtc": None,
                "IsActive": True,
            })),
            FakeResult(FakeRow({"UserId": "user-1", "UpdatedUtc": None})),
            FakeResult(FakeRow({
                "ConsentVersion": "my-quivrr-consent-v1",
                "MarketingConsent": False,
                "AnalyticsConsent": False,
                "ProductNotificationConsent": False,
                "ConsentCapturedUtc": None,
                "ConsentSource": "automatic_first_login_default",
            })),
        ]
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_connection
        fake_context.__exit__.return_value = None

        with patch.object(backend_app.engine, "begin", return_value=fake_context):
            bundle = backend_app.ensure_identity_user({
                "entraObjectId": "entra-1",
                "email": "surfer@example.com",
                "displayName": "Test Surfer",
                "identityProvider": "microsoft",
            })

        self.assertTrue(bundle["isNewUser"])
        self.assertEqual(bundle["user"]["EntraObjectId"], "entra-1")
        executed_sql = "\n".join(str(call.args[0]) for call in fake_connection.execute.call_args_list)
        self.assertIn("INSERT INTO dbo.Users", executed_sql)
        self.assertIn("INSERT INTO dbo.UserConsents", executed_sql)

    def test_token_claims_normalise_email_and_provider(self):
        with patch.object(entra_external_id, "validate_access_token", return_value={
            "oid": "entra-1",
            "sub": "subject-1",
            "emails": ["surfer@example.com"],
            "name": "Test Surfer",
            "idp": "google.com",
        }):
            user = entra_external_id.get_current_user_optional("Bearer token")

        self.assertEqual(user["entraObjectId"], "entra-1")
        self.assertEqual(user["email"], "surfer@example.com")
        self.assertEqual(user["identityProvider"], "google.com")

    def test_events_endpoint_accepts_anonymous_payload(self):
        fake_connection = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_connection
        fake_context.__exit__.return_value = None

        with patch.object(backend_app.engine, "begin", return_value=fake_context):
            response = self.client.post(
                "/api/events",
                json={
                    "anonymousSessionId": "anon-session-1",
                    "eventType": "SearchPerformed",
                    "regionCode": "AU",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "persisted")
        self.assertFalse(body["authenticated"])
        self.assertEqual(body["anonymousSessionId"], "anon-session-1")
        self.assertEqual(body["eventType"], "SearchPerformed")

    def test_saved_boards_endpoint_returns_saved_items(self):
        bundle = {
            "isNewUser": False,
            "user": {"UserId": "user-1", "EntraObjectId": "entra-1", "Email": "surfer@example.com"},
            "profile": {},
            "consent": {},
        }
        saved_boards = [{
            "savedBoardId": "saved-1",
            "brandName": "Album",
            "modelName": "Bom Dia",
            "regionCode": "AU",
            "title": "Album | Bom Dia | PU | 5'6 | 27.1L",
        }]
        fake_connection = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_connection
        fake_context.__exit__.return_value = None

        with patch.object(backend_app, "resolve_persisted_identity_bundle", return_value=bundle), patch.object(
            backend_app.engine, "connect", return_value=fake_context
        ), patch.object(backend_app, "fetch_saved_boards", return_value=saved_boards):
            response = self.client.get("/api/my-quivrr/saved-boards", headers={"Authorization": "Bearer token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["savedBoards"][0]["savedBoardId"], "saved-1")

    def test_saved_board_post_requires_board_reference(self):
        bundle = {
            "isNewUser": False,
            "user": {"UserId": "user-1", "EntraObjectId": "entra-1", "Email": "surfer@example.com"},
            "profile": {},
            "consent": {},
        }

        with patch.object(backend_app, "resolve_persisted_identity_bundle", return_value=bundle):
            response = self.client.post(
                "/api/my-quivrr/saved-boards",
                headers={"Authorization": "Bearer token"},
                json={"regionCode": "AU"},
            )

        self.assertEqual(response.status_code, 422)

    def test_quiver_endpoint_returns_items(self):
        bundle = {
            "isNewUser": False,
            "user": {"UserId": "user-1", "EntraObjectId": "entra-1", "Email": "surfer@example.com"},
            "profile": {},
            "consent": {},
        }
        quiver_items = [{
            "quiverId": "quiver-1",
            "title": "Custom Twin",
            "customBoard": True,
            "currentBoard": True,
        }]
        fake_connection = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_connection
        fake_context.__exit__.return_value = None

        with patch.object(backend_app, "resolve_persisted_identity_bundle", return_value=bundle), patch.object(
            backend_app.engine, "connect", return_value=fake_context
        ), patch.object(backend_app, "fetch_user_quiver", return_value=quiver_items):
            response = self.client.get("/api/my-quivrr/quiver", headers={"Authorization": "Bearer token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertTrue(response.json()["quiver"][0]["customBoard"])

    def test_quiver_post_accepts_custom_board(self):
        bundle = {
            "isNewUser": False,
            "user": {"UserId": "user-1", "EntraObjectId": "entra-1", "Email": "surfer@example.com"},
            "profile": {},
            "consent": {},
        }
        fake_connection = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_connection
        fake_context.__exit__.return_value = None
        quiver_items = [{
            "quiverId": "generated-quiver-id",
            "title": "Album Twin",
            "customBoard": True,
            "currentBoard": False,
        }]

        with patch.object(backend_app, "resolve_persisted_identity_bundle", return_value=bundle), patch.object(
            backend_app.engine, "begin", return_value=fake_context
        ), patch.object(backend_app, "fetch_user_quiver", return_value=quiver_items):
            response = self.client.post(
                "/api/my-quivrr/quiver",
                headers={"Authorization": "Bearer token"},
                json={
                    "customBoard": True,
                    "customBrandName": "Album",
                    "customModelName": "Twin Thing",
                    "status": "Favourite board",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "created")
        self.assertEqual(response.json()["quiver"][0]["quiverId"], "generated-quiver-id")

    def test_profile_endpoint_includes_recent_activity_counts(self):
        bundle = {
            "isNewUser": False,
            "user": {
                "UserId": "user-1",
                "EntraObjectId": "entra-1",
                "Email": "surfer@example.com",
                "DisplayName": "Test Surfer",
                "IdentityProvider": "entra_external_id",
                "HomeRegion": "AU",
                "CreatedUtc": None,
                "LastLoginUtc": None,
            },
            "profile": {"PreferredBrands": '["Album"]'},
            "consent": {},
        }
        fake_connection = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_connection
        fake_context.__exit__.return_value = None

        with patch.object(backend_app, "resolve_persisted_identity_bundle", return_value=bundle), patch.object(
            backend_app.engine, "connect", return_value=fake_context
        ), patch.object(backend_app, "fetch_recent_activity", return_value=[{"eventType": "BoardViewed"}]), patch.object(
            backend_app, "fetch_saved_boards", return_value=[{"savedBoardId": "saved-1"}]
        ), patch.object(
            backend_app, "fetch_user_quiver", return_value=[{"quiverId": "quiver-1", "currentBoard": True}]
        ):
            response = self.client.get("/api/my-quivrr/profile", headers={"Authorization": "Bearer token"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["savedBoardsCount"], 1)
        self.assertEqual(body["quiverCount"], 1)
        self.assertEqual(body["currentBoardCount"], 1)
        self.assertEqual(body["recentActivity"][0]["eventType"], "BoardViewed")

    def test_profile_completion_strength_distinguishes_partial_and_strong(self):
        partial_strength = backend_app.profile_strength(
            {"HomeRegion": None},
            {
                "Ability": "Progressing",
                "WaveType": "Beach break",
                "SurfFrequency": "Weekly",
            },
        )
        strong_strength = backend_app.profile_strength(
            {"HomeRegion": "AU"},
            {
                "HeightCm": 180,
                "WeightKg": 78,
                "Ability": "Intermediate",
                "CurrentVolumeLitres": 30.0,
                "WaveType": "Beach break",
            },
        )

        self.assertEqual(partial_strength, "partial")
        self.assertEqual(strong_strength, "strong")

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
        quiver_script = Path("sql/identity/002_create_my_quivrr_quiver.sql")
        self.assertTrue(quiver_script.exists())
        self.assertIn("dbo.UserQuiver", quiver_script.read_text(encoding="utf-8"))
        profile_extension_script = Path("sql/identity/003_extend_my_quivrr_profiles_onboarding.sql")
        self.assertTrue(profile_extension_script.exists())
        extension_text = profile_extension_script.read_text(encoding="utf-8")
        self.assertIn("CurrentBoard", extension_text)
        self.assertIn("SurfingGoal", extension_text)


if __name__ == "__main__":
    unittest.main()
