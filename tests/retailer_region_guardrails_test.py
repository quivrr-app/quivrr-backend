import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


class RetailerRegionGuardrailTests(unittest.TestCase):
    def test_all_python_inventory_inserts_include_region_code(self):
        insert_pattern = re.compile(
            r"INSERT\s+INTO\s+dbo\.RetailerInventory\s*\((.*?)\)\s*VALUES",
            re.IGNORECASE | re.DOTALL,
        )
        matches = []
        for path in list((ROOT / "scripts").rglob("*.py")) + list(
            (ROOT / "scrapers").rglob("*.py")
        ):
            text = path.read_text(encoding="utf-8")
            for columns in insert_pattern.findall(text):
                matches.append(path)
                self.assertRegex(
                    columns,
                    r"\bRegionCode\b",
                    f"RetailerInventory insert omits RegionCode: {path}",
                )
        self.assertTrue(matches, "No RetailerInventory inserts were found")

    def test_au_full_refresh_delete_is_region_scoped(self):
        text = source("scripts/import_retailer_inventory.py")
        self.assertNotRegex(
            text,
            r"DELETE\s+FROM\s+dbo\.RetailerInventory\s*;",
        )
        self.assertRegex(
            text,
            r"DELETE\s+FROM\s+dbo\.RetailerInventory\s+"
            r"WHERE\s+RegionCode\s*=\s*:region_code",
        )
        self.assertIn('REGION_CODE = "AU"', text)

    def test_slimes_delete_and_insert_are_au_scoped(self):
        text = source("scripts/import_slimes_newcastle_inventory.py")
        self.assertRegex(
            text,
            r"DELETE\s+FROM\s+dbo\.RetailerInventory\s+"
            r"WHERE\s+RetailerId\s*=\s*:retailer_id\s+"
            r"AND\s+RegionCode\s*=\s*:region_code",
        )
        self.assertIn('REGION_CODE = "AU"', text)

    def test_nightly_brand_reconciliation_is_au_scoped(self):
        text = source("scripts/reconcile_retailer_inventory_brands.py")
        self.assertRegex(
            text,
            r"(?s)UPDATE\s+dbo\.RetailerInventory.*?"
            r"WHERE.*?RegionCode\s*=\s*'AU'",
        )


if __name__ == "__main__":
    unittest.main()
