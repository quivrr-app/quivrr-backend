
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(dotenv_path=Path(".env"))

BRAND_ALIASES = {
    "JS Industries": ["JS", "JS Industries"],
    "Channel Islands": ["Channel Islands", "CI Surfboards", "Al Merrick"],
    "Lost": ["Lost", "Mayhem", "Lost Surfboards"],
    "Haydenshapes": ["Haydenshapes", "Hayden Shapes"],
    "Sharp Eye": ["Sharp Eye", "Sharpeye", "SharpEye"],
    "Pyzel": ["Pyzel"],
    "DHD": ["DHD", "Darren Handley"],
    "Firewire": ["Firewire", "Slater Designs", "Slater"],
    "Rusty": ["Rusty"],
    "Chilli": ["Chilli"],
    "Album": ["Album", "Album Surf", "Album Surfboards"],
    "Misfit Shapes": ["Misfit", "Misfit Shapes"],
    "Chemistry Surfboards": ["Chemistry", "Chemistry Surfboards"],
    "DMS Surfboards": ["DMS", "DMS Surfboards"],
}

cs = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={os.getenv('SQL_SERVER')};"
    f"DATABASE={os.getenv('SQL_DATABASE')};"
    f"UID={os.getenv('SQL_USERNAME')};"
    f"PWD={os.getenv('SQL_PASSWORD')};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
    f"Connection Timeout=30;"
)

engine = create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(cs)}")

with engine.begin() as conn:
    print("")
    print("Reconciling retailer inventory brand mappings")
    print("=" * 80)

    total = 0

    for canonical_brand, aliases in BRAND_ALIASES.items():
        brand_id = conn.execute(text("""
            SELECT BrandId
            FROM dbo.Brands
            WHERE BrandName = :brand_name
              AND IsActive = 1
        """), {"brand_name": canonical_brand}).scalar()

        if not brand_id:
            print(f"Skipped missing canonical brand: {canonical_brand}")
            continue

        updated_for_brand = 0

        for alias in aliases:
            result = conn.execute(text("""
                UPDATE dbo.RetailerInventory
                SET BrandId = :brand_id
                WHERE IsActive = 1
                  AND (
                      BrandId IS NULL
                      OR BrandId <> :brand_id
                  )
                  AND (
                      RawProductTitle LIKE :alias
                      OR NormalisedProductTitle LIKE :alias
                  )
            """), {
                "brand_id": brand_id,
                "alias": f"%{alias}%",
            })

            updated_for_brand += result.rowcount or 0

        total += updated_for_brand
        print(f"{canonical_brand}: {updated_for_brand} rows reconciled")

    print("")
    print(f"Total rows reconciled: {total}")
    print("")

    rows = conn.execute(text("""
        SELECT
            b.BrandName,
            COUNT(*) AS InventoryRows,
            COUNT(DISTINCT ri.RetailerId) AS RetailerCount
        FROM dbo.RetailerInventory ri
        JOIN dbo.Brands b ON b.BrandId = ri.BrandId
        WHERE ri.IsActive = 1
        GROUP BY b.BrandName
        ORDER BY b.BrandName
    """)).fetchall()

    for row in rows:
        print(dict(row._mapping))
