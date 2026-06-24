import io
import json
import unittest
from contextlib import redirect_stdout

from utils.structured_logging import build_event, emit_event, utc_timestamp


class StructuredLoggingTests(unittest.TestCase):
    def test_timestamp_generation_uses_utc_z_format(self):
        value = utc_timestamp()
        self.assertTrue(value.endswith("Z"))
        self.assertIn("T", value)

    def test_secret_fields_are_redacted(self):
        payload = build_event(
            "inventory_refresh_started",
            "retailer_inventory",
            password="abc123",
            api_key="secret-value",
            normal_field="safe",
        )
        self.assertEqual(payload["password"], "[REDACTED]")
        self.assertEqual(payload["api_key"], "[REDACTED]")
        self.assertEqual(payload["normal_field"], "safe")

    def test_single_line_json_is_emitted(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            emit_event("inventory_refresh_started", "retailer_inventory", region="EU", status="success", rows=10)
        line = buffer.getvalue().strip()
        parsed = json.loads(line)
        self.assertEqual(parsed["event"], "inventory_refresh_started")
        self.assertEqual(parsed["region"], "EU")
        self.assertEqual(parsed["rows"], 10)


if __name__ == "__main__":
    unittest.main()
