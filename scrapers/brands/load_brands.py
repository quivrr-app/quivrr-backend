import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_FILE = PROJECT_ROOT / "scrapers" / "brands" / "brands_seed.json"

load_dotenv(PROJECT_ROOT / ".env")


def build_connection_string() -> str:
    odbc_string = (
        f"DRIVER={{{os.getenv('SQL_DRIVER')}}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USERNAME')};"
        f"PWD={os.getenv('SQL_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_string)}"


def load_seed_data() -> list[dict]:
    with open(SEED_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def upsert_brand(connection, brand: dict) -> None:
    query = text("""
        IF EXISTS (
            SELECT 1
            FROM dbo.Brands
            WHERE BrandName = :brand_name
        )
        BEGIN
            UPDATE dbo.Brands
            SET
                OfficialWebsiteUrl = :website,
                Country = :country,
                IsActive = 1,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE BrandName = :brand_name
        END
        ELSE
        BEGIN
            INSERT INTO dbo.Brands (
                BrandName,
                OfficialWebsiteUrl,
                Country,
                IsActive
            )
            VALUES (
                :brand_name,
                :website,
                :country,
                1
            )
        END
    """)

    connection.execute(query, brand)


def main() -> None:
    brands = load_seed_data()
    engine = create_engine(build_connection_string())

    with engine.begin() as connection:
        for brand in brands:
            upsert_brand(connection, brand)

    print(f"Loaded {len(brands)} brands into Azure SQL.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Brand load failed: {error}")
        sys.exit(1)