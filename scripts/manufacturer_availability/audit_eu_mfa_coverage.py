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
    "Firewire": ("https://eu.firewiresurfboards.com/collections/prestige-surfboards", "Shopify", "Implemented", True, True, True, True, True, "Maintain EU refresh."),
    "Haydenshapes": ("https://eu.haydenshapes.com/collections/in-stock-surfboards", "Shopify", "Implemented", True, True, True, True, True, "Improve canonical model coverage."),
    "Pyzel": ("https://europe.pyzelsurfboards.com/collections/all-surfboards", "Shopify", "Implemented", True, True, True, True, True, "Improve canonical BoardSize coverage."),
    "Rusty": ("https://rustysurfboards.eu/collections/surfboards", "Shopify", "Implemented", True, True, True, True, True, "Improve deterministic model aliases."),
    "Sharp Eye": ("https://sharpeyesurfboardseurope.com/collections/shop-surfboards", "Shopify", "Implemented", True, True, True, False, True, "Product listings lack reliable dimensions."),
    "JS Industries": ("https://www.jsindustries.eu/collections/all-surfboards", "Shopify + embedded stock board data", "Implemented", True, True, True, True, True, "Maintain parent-variant mapping."),
    "DHD": ("https://www.dhdsurf.eu/gb/510-surfboards", "PrestaShop", "Implemented", True, True, True, True, True, "Maintain the dedicated EU parser."),
    "Lost": ("https://lostenterprises.eu/", "Shopify", "Not applicable", False, False, False, False, True, "EU storefront exposes apparel, not direct surfboard stock."),
    "Album": (None, "Unknown", "Blocked", False, False, False, False, False, "No validated EU-specific direct board storefront."),
    "Channel Islands": (None, "Unknown", "Blocked", False, False, False, False, False, "No public EU direct-stock endpoint; EU dealer presence is not manufacturer stock."),
    "Chemistry Surfboards": ("https://chemistrysurfboards.com/", "Shopify", "Blocked", True, True, True, True, True, "Storefront is not EU-specific and does not prove EU-held stock."),
    "Chilli": (None, "Unknown", "Blocked", False, False, False, False, False, "No validated EU direct-stock source."),
    "Christenson": (None, "Unknown", "Blocked", False, False, False, False, False, "No validated EU direct-stock source."),
    "DMS Surfboards": ("https://dmshapes.com/", "Shopify", "Blocked", True, True, True, True, True, "Current direct storefront is not EU-specific."),
    "Misfit Shapes": ("https://misfitshapes.com/", "Shopify", "Blocked", True, True, True, True, True, "EU fulfilment and EU-held stock are not validated."),
    "Pukas": ("https://pukassurfshop.com/", "Shopify", "Partially implemented", True, True, True, True, True, "Source is multi-brand retail inventory; isolate true Pukas manufacturer-direct stock before MFA."),
    "Simon Anderson": (None, "Unknown", "Blocked", False, False, False, False, False, "No validated EU direct-stock source."),
}

TARGET_BRANDS = list(PLAN)


def main():
    with connect_with_retry(build_engine()) as conn:
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
    for brand in TARGET_BRANDS:
        source, platform, status, products, variants, stock, dimensions, price, action = PLAN[brand]
        rows.append({"BrandName": brand, "AuMfaRows": counts.get((brand, "AU"), 0),
                     "EuMfaRows": counts.get((brand, "EU"), 0), "EuSourceUrl": source,
                     "Platform": platform, "ProductsVisible": products, "VariantsVisible": variants,
                     "StockStateVisible": stock, "DimensionsVisible": dimensions, "PriceVisible": price,
                     "EuStatus": status, "ExactBlockerOrNextAction": action})
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__": main()
