from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.europe.import_eu_retailer_inventory import build_engine, connect_with_retry  # noqa: E402

OUTPUT_JSON = Path("scripts/manufacturer_availability/output/eu_mfa_brand_coverage.json")
OUTPUT_CSV = Path("scripts/manufacturer_availability/output/eu_mfa_brand_coverage.csv")

PLAN = {
    "Firewire": ("https://eu.firewiresurfboards.com/collections/prestige-surfboards", "Implemented", "Maintain Shopify EU refresh."),
    "Haydenshapes": ("https://eu.haydenshapes.com/collections/in-stock-surfboards", "Implemented", "Improve canonical model and size coverage."),
    "Pyzel": ("https://europe.pyzelsurfboards.com/collections/all-surfboards", "Implemented", "Improve BoardSize catalogue alignment."),
    "Rusty": ("https://rustysurfboards.eu/collections/surfboards", "Implemented", "Improve deterministic model aliases and sizes."),
    "Sharp Eye": ("https://sharpeyesurfboardseurope.com/collections/shop-surfboards", "Implemented", "Source dimensions from product detail data."),
    "JS Industries": ("https://www.jsindustries.eu/collections/all-surfboards", "Implemented", "Maintain deterministic aliases; add BoardSizes only where dimensions uniquely identify a canonical size."),
    "DHD": ("https://www.dhdsurf.eu/gb/510-surfboards", "Implemented", "Maintain the PrestaShop adapter; expand canonical BoardSizes without forcing ambiguous matches."),
    "Lost": ("https://lostenterprises.eu/", "Not applicable", "EU storefront currently exposes apparel, not direct surfboard stock."),
    "Album": (None, "Blocked", "Find and validate a mainland-EU direct stock source."),
    "Channel Islands": (None, "Blocked", "Find and validate a mainland-EU direct stock source."),
    "Chemistry Surfboards": (None, "Blocked", "Current direct source is not EU-specific."),
    "Chilli": (None, "Blocked", "Find and validate a mainland-EU direct stock source."),
    "Christenson": (None, "Blocked", "Find and validate a mainland-EU direct stock source."),
    "DMS Surfboards": (None, "Blocked", "Current direct source is not EU-specific."),
    "Misfit Shapes": (None, "Blocked", "Validate EU fulfilment before enabling global storefront stock."),
    "Pukas": (None, "Blocked", "Separate manufacturer-direct Pukas stock from multi-brand retail stock."),
    "Simon Anderson": (None, "Blocked", "Find and validate a mainland-EU direct stock source."),
}


def main():
    with connect_with_retry(build_engine()) as conn:
        brands = [row.BrandName for row in conn.execute(text("SELECT BrandName FROM dbo.Brands ORDER BY BrandName"))]
        counts = {
            (row.BrandName, row.RegionCode): int(row.InventoryRows)
            for row in conn.execute(text("""
                SELECT b.BrandName, mi.RegionCode, COUNT(*) AS InventoryRows
                FROM dbo.ManufacturerInventory mi
                JOIN dbo.Brands b ON b.BrandId = mi.BrandId
                GROUP BY b.BrandName, mi.RegionCode
            """))
        }
    rows = []
    for brand in brands:
        source, status, action = PLAN.get(
            brand, (None, "Not investigated", "Investigate whether a valid EU direct surfboard source exists.")
        )
        rows.append({"BrandName": brand, "AuMfaRows": counts.get((brand, "AU"), 0),
                     "EuMfaRows": counts.get((brand, "EU"), 0), "EuSourceUrl": source,
                     "EuStatus": status, "RecommendedNextAction": action})
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__": main()
