import unittest
from datetime import datetime
from decimal import Decimal

from scripts.usa import import_us_retailer_inventory as us_importer


class UsImportDecimalPrecisionTests(unittest.TestCase):
    def test_conform_inventory_payload_for_sql_quantizes_schema_bound_decimals(self):
        payload = {
            "price_amount": Decimal("1.71000"),
            "volume": Decimal("36.2"),
            "confidence": 11.0,
            "estimated_shipping_aud": Decimal("12.345"),
        }

        conformed = us_importer.conform_inventory_payload_for_sql(payload)

        self.assertEqual(conformed["price_amount"], 1.71)
        self.assertEqual(conformed["volume"], 36.20)
        self.assertEqual(conformed["confidence"], 11.00)
        self.assertEqual(conformed["estimated_shipping_aud"], 12.35)

    def test_conform_inventory_payload_for_sql_uses_half_up_rounding_without_mutating_source(self):
        payload = {
            "price_amount": Decimal("1.57500"),
            "volume": Decimal("29.995"),
            "confidence": Decimal("8.125"),
        }

        conformed = us_importer.conform_inventory_payload_for_sql(payload)

        self.assertEqual(conformed["price_amount"], 1.58)
        self.assertEqual(conformed["volume"], 30.00)
        self.assertEqual(conformed["confidence"], 8.13)
        self.assertEqual(payload["price_amount"], Decimal("1.57500"))
        self.assertEqual(payload["volume"], Decimal("29.995"))
        self.assertEqual(payload["confidence"], Decimal("8.125"))

    def test_to_json_safe_converts_nested_decimals_in_rollback_payloads(self):
        payload = {
            "insertedInventoryIds": [1, 2],
            "updatedRowsBefore": [
                {
                    "price_amount": Decimal("649.00"),
                    "volume": Decimal("36.20"),
                    "nested": {"confidence": Decimal("8.13")},
                }
            ],
        }

        result = us_importer.to_json_safe(payload)

        self.assertEqual(
            result,
            {
                "insertedInventoryIds": [1, 2],
                "updatedRowsBefore": [
                    {
                        "price_amount": 649.0,
                        "volume": 36.2,
                        "nested": {"confidence": 8.13},
                    }
                ],
            },
        )
        self.assertEqual(
            payload["updatedRowsBefore"][0]["price_amount"], Decimal("649.00")
        )

    def test_to_json_safe_converts_datetimes_to_iso_strings(self):
        timestamp = datetime(2026, 6, 25, 14, 10, 9)

        result = us_importer.to_json_safe({"updated_at": timestamp})

        self.assertEqual(result, {"updated_at": "2026-06-25T14:10:09"})


if __name__ == "__main__":
    unittest.main()
