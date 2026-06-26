import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as backend_app


def official_board(**overrides):
    payload = {
        "BoardSizeId": 188217,
        "BoardModelId": 501,
        "BrandId": 77,
        "BrandName": "Album",
        "ModelName": "Bom Dia",
        "OfficialProductUrl": "https://example.com/album/bom-dia",
        "LengthFeetInches": "5'6",
        "Width": '19 3/4"',
        "Thickness": '2 1/2"',
        "VolumeLitres": 28.5,
        "Construction": "PU",
        "FinSetup": "Thruster",
        "TailShape": "Round",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def retailer_row(**overrides):
    payload = {
        "InventoryId": 1001,
        "RetailerName": "Example Surf",
        "WebsiteUrl": "https://retailer.example.com",
        "LogoUrl": "https://retailer.example.com/logo.png",
        "RawProductTitle": 'Album Sunstone 6\'2 x 20 1/4" x 2 5/8" 34.1L',
        "NormalisedProductTitle": "album sunstone 6 2 20 1 4 2 5 8 34 1l",
        "ProductUrl": "https://retailer.example.com/album-sunstone",
        "ProductImageUrl": "https://retailer.example.com/album-sunstone.jpg",
        "PriceAud": None,
        "PriceAmount": 999.0,
        "PriceCurrency": "AUD",
        "StockStatus": "in stock",
        "Construction": "PU",
        "FinSetup": "Thruster",
        "LengthFeetInches": "6'2",
        "Width": '20 1/4"',
        "Thickness": '2 5/8"',
        "VolumeLitres": 34.1,
        "BrandId": 77,
        "BoardModelId": 888,
        "BoardSizeId": 3001,
        "MatchScore": 220,
        "CanonicalModelName": "Sunstone",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class SearchFallbackTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(backend_app.app)

    def test_fallback_returns_top_level_other_model_matches_for_broader_same_brand_pool(self):
        with patch.object(backend_app, "OTHER_MODEL_MATCHES_ENABLED", True), patch.object(
            backend_app,
            "fetch_one_with_retry",
            return_value=official_board(),
        ), patch.object(
            backend_app,
            "execute_with_retry",
            side_effect=[
                [],
                [],
                [],
                [],
                [retailer_row()],
            ],
        ):
            response = self.client.get("/api/search?boardSizeId=188217&region=AU")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            body["searchVersion"],
            "search_timeout_fix_v2_thin_fallback_v1_broader_brand_fallback_exact_gate_sprint6_1_legacy_brand_rows",
        )
        self.assertEqual(body["exactRetailerMatches"], [])
        self.assertEqual(body["closeRetailerMatches"], [])
        self.assertEqual(len(body["otherModelMatches"]), 1)
        self.assertEqual(body["otherModelMatches"][0]["title"], 'Album Sunstone 6\'2 x 20 1/4" x 2 5/8" 34.1L')
        self.assertEqual(body["otherModelMatches"][0]["canonicalModelName"], "Sunstone")

    def test_fallback_is_suppressed_when_exact_match_exists(self):
        exact_row = retailer_row(
            InventoryId=1002,
            RawProductTitle='Album Bom Dia 5\'6 x 19 3/4" x 2 1/2" 28.5L',
            NormalisedProductTitle="album bom dia 5 6 19 3 4 2 1 2 28 5l",
            LengthFeetInches="5'6",
            Width='19 3/4"',
            Thickness='2 1/2"',
            VolumeLitres=28.5,
            BoardModelId=501,
            BoardSizeId=188217,
        )
        with patch.object(backend_app, "OTHER_MODEL_MATCHES_ENABLED", True), patch.object(
            backend_app,
            "fetch_one_with_retry",
            return_value=official_board(),
        ), patch.object(
            backend_app,
            "execute_with_retry",
            side_effect=[
                [],
                [],
                [exact_row],
                [],
            ],
        ) as execute_mock:
            response = self.client.get("/api/search?boardSizeId=188217&region=US")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["exactRetailerMatches"]), 1)
        self.assertEqual(body["otherModelMatches"], [])
        self.assertEqual(execute_mock.call_count, 4)

    def test_fallback_does_not_require_canonical_model_link_for_same_brand_row(self):
        legacy_row = retailer_row(
            InventoryId=1003,
            RawProductTitle='Rusty Blade 6\'0 x 20" x 2 1/2" 33.5L',
            NormalisedProductTitle="rusty blade 6 0 20 2 1 2 33 5l",
            ProductUrl="https://retailer.example.com/rusty-blade",
            BrandId=10,
            BoardModelId=None,
            BoardSizeId=None,
            CanonicalModelName=None,
        )
        with patch.object(backend_app, "OTHER_MODEL_MATCHES_ENABLED", True), patch.object(
            backend_app,
            "fetch_one_with_retry",
            return_value=official_board(
                BrandId=10,
                BrandName="Rusty",
                BoardModelId=7904,
                ModelName="1984",
                OfficialProductUrl="https://rustysurfboards.com/collections/1984",
                Construction="Standard",
            ),
        ), patch.object(
            backend_app,
            "execute_with_retry",
            side_effect=[
                [],
                [],
                [],
                [],
                [legacy_row],
            ],
        ):
            response = self.client.get("/api/search?boardSizeId=185196&region=AU")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["exactRetailerMatches"], [])
        self.assertEqual(body["closeRetailerMatches"], [])
        self.assertEqual(len(body["otherModelMatches"]), 1)
        self.assertIsNone(body["otherModelMatches"][0]["canonicalModelName"])


if __name__ == "__main__":
    unittest.main()
