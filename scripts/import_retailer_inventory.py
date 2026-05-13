import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text


load_dotenv()

INPUT_FILE = Path("scrapers/products/output/normalised_surfboards.json")

EXCLUDED_RETAILERS = {
    "js industries",
    "firewire",
    "slater designs",
    "lost surfboards",
    "mayhem",
    "pyzel",
    "channel islands",
    "ci surfboards",
    "haydenshapes",
    "dhd",
    "sharp eye",
    "sharpeye",
    "album",
    "christenson",
    "aipa",
    "chilli",
    "rusty",
    "pukas",
    "mctavish",
    "nsp",
    "walden",
    "dark arts",
}


def require_env(name):
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value.strip()


def build_connection_string():
    server = require_env("SQL_SERVER")
    database = require_env("SQL_DATABASE")
    username = require_env("SQL_USERNAME")
    password = require_env("SQL_PASSWORD")
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server").strip()

    server = server.replace("tcp:", "").strip()

    if not server.endswith(".database.windows.net"):
        raise RuntimeError(
            "SQL_SERVER must be the Azure SQL server host only, for example "
            "quivrr-sql-prod.database.windows.net"
        )

    odbc_string = (
        f"Driver={{{driver}}};"
        f"Server=tcp:{server},1433;"
        f"Database={database};"
        f"Uid={username};"
        f"Pwd={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
    )

    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_string)


engine = create_engine(
    build_connection_string(),
    pool_pre_ping=True,
    pool_recycle=1800,
)


@event.listens_for(engine, "before_cursor_execute")
def enable_fast_executemany(
    conn,
    cursor,
    statement,
    parameters,
    context,
    executemany,
):
    if executemany:
        cursor.fast_executemany = True


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def clean_key(value):
    value = clean(value)

    if value is None:
        return ""

    return value.lower()


def money(value):
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def decimal_or_none(value):
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def first_image(images):
    if isinstance(images, list) and images:
        return clean(images[0])

    return None


def is_excluded_retailer(retailer_name):
    retailer_key = clean_key(retailer_name)

    return retailer_key in EXCLUDED_RETAILERS


def row_dedupe_key(row):
    return "|".join([
        clean_key(row.get("retailer_name")),
        clean_key(row.get("product_url")),
        clean_key(row.get("raw_title")),
        clean_key(row.get("length")),
        str(row.get("volume") or ""),
        str(row.get("price") or ""),
    ])


def has_column(connection, table_name, column_name):
    result = connection.execute(
        text("""
            SELECT COUNT(*) AS ColumnCount
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
            AND TABLE_NAME = :table_name
            AND COLUMN_NAME = :column_name
        """),
        {
            "table_name": table_name,
            "column_name": column_name,
        },
    ).fetchone()

    return result.ColumnCount > 0


def main():
    print("\nImporting available retailer inventory into SQL...\n")

    if not INPUT_FILE.exists():
        raise RuntimeError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        inventory = json.load(file)

    available_inventory = [
        item for item in inventory
        if item.get("available") is True
    ]

    print(f"Rows loaded: {len(inventory)}")
    print(f"Available rows selected: {len(available_inventory)}")

    rows_before_dedupe = []
    excluded_manufacturer_rows = 0

    for item in available_inventory:
        retailer_name = clean(item.get("retailer"))

        if not retailer_name:
            continue

        if is_excluded_retailer(retailer_name):
            excluded_manufacturer_rows += 1
            continue

        raw_brand = clean(item.get("brand")) or clean(item.get("vendor"))

        rows_before_dedupe.append({
            "retailer_name": retailer_name,
            "website_url": clean(item.get("website")),
            "raw_brand": raw_brand,
            "raw_title": clean(item.get("title")),
            "normalised_title": clean(item.get("model_key")),
            "product_url": clean(item.get("product_url")),
            "image_url": first_image(item.get("images")),
            "price": money(item.get("price")),
            "stock_status": "In Stock",
            "construction": clean(item.get("construction")),
            "fin_setup": clean(item.get("fin_system")),
            "length": clean(item.get("length")),
            "width": clean(item.get("width")),
            "thickness": clean(item.get("thickness")),
            "volume": decimal_or_none(item.get("volume_litres")),
            "confidence": decimal_or_none(item.get("surfboard_confidence")),
        })

    deduped_rows_by_key = {}

    for row in rows_before_dedupe:
        key = row_dedupe_key(row)

        if key not in deduped_rows_by_key:
            deduped_rows_by_key[key] = row
            continue

        existing = deduped_rows_by_key[key]

        if not existing.get("image_url") and row.get("image_url"):
            existing["image_url"] = row.get("image_url")

        if not existing.get("confidence") and row.get("confidence"):
            existing["confidence"] = row.get("confidence")

    rows_to_import = list(deduped_rows_by_key.values())

    print(f"Manufacturer/direct brand rows excluded: {excluded_manufacturer_rows}")
    print(f"Rows before dedupe: {len(rows_before_dedupe)}")
    print(f"Rows after dedupe: {len(rows_to_import)}")
    print(f"Duplicate rows removed: {len(rows_before_dedupe) - len(rows_to_import)}")

    retailer_keys = {}

    for row in rows_to_import:
        retailer_name = clean(row.get("retailer_name"))
        website = clean(row.get("website_url"))

        if not retailer_name:
            continue

        key = retailer_name.lower()

        if key not in retailer_keys:
            retailer_keys[key] = {
                "retailer_name": retailer_name,
                "website_url": website,
            }

    with engine.begin() as connection:
        retailer_has_logo = has_column(
            connection,
            "Retailers",
            "LogoUrl",
        )

        inventory_has_confidence = has_column(
            connection,
            "RetailerInventory",
            "InventoryConfidenceScore",
        )

        print(f"Retailers found in available inventory: {len(retailer_keys)}")
        print(f"Retailers.LogoUrl exists: {retailer_has_logo}")
        print(
            "RetailerInventory.InventoryConfidenceScore exists: "
            f"{inventory_has_confidence}"
        )

        existing_retailers = {
            row.RetailerName.lower(): row.RetailerId
            for row in connection.execute(
                text("""
                    SELECT
                        RetailerId,
                        RetailerName
                    FROM dbo.Retailers
                """)
            )
        }

        for key, retailer in retailer_keys.items():
            if key in existing_retailers:
                continue

            result = connection.execute(
                text("""
                    INSERT INTO dbo.Retailers (
                        RetailerName,
                        WebsiteUrl,
                        Country,
                        IsActive,
                        CreatedAtUtc,
                        UpdatedAtUtc
                    )
                    OUTPUT INSERTED.RetailerId
                    VALUES (
                        :retailer_name,
                        :website_url,
                        'Australia',
                        1,
                        GETUTCDATE(),
                        GETUTCDATE()
                    )
                """),
                retailer,
            ).fetchone()

            existing_retailers[key] = result.RetailerId

        brands = {
            row.BrandName.lower(): row.BrandId
            for row in connection.execute(
                text("""
                    SELECT
                        BrandId,
                        BrandName
                    FROM dbo.Brands
                    WHERE IsActive = 1
                """)
            )
        }

        print("Cleaning existing retailer inventory...")

        connection.execute(
            text("""
                DELETE FROM dbo.RetailerInventory;
            """)
        )

        insert_rows = []

        for row in rows_to_import:
            retailer_name = clean(row.get("retailer_name"))

            if not retailer_name:
                continue

            retailer_id = existing_retailers.get(
                retailer_name.lower()
            )

            if retailer_id is None:
                continue

            raw_brand = clean(row.get("raw_brand"))

            brand_id = None

            if raw_brand:
                brand_id = brands.get(raw_brand.lower())

            insert_rows.append({
                "retailer_id": retailer_id,
                "brand_id": brand_id,
                "raw_title": clean(row.get("raw_title")),
                "normalised_title": clean(row.get("normalised_title")),
                "product_url": clean(row.get("product_url")),
                "image_url": clean(row.get("image_url")),
                "price": row.get("price"),
                "stock_status": clean(row.get("stock_status")) or "In Stock",
                "construction": clean(row.get("construction")),
                "fin_setup": clean(row.get("fin_setup")),
                "length": clean(row.get("length")),
                "width": clean(row.get("width")),
                "thickness": clean(row.get("thickness")),
                "volume": row.get("volume"),
                "confidence": row.get("confidence"),
            })

        print(f"Batch inserting available inventory rows: {len(insert_rows)}")

        if insert_rows:
            connection.execute(
                text("""
                    INSERT INTO dbo.RetailerInventory (
                        RetailerId,
                        BrandId,
                        BoardModelId,
                        BoardSizeId,
                        RawProductTitle,
                        NormalisedProductTitle,
                        ProductUrl,
                        ProductImageUrl,
                        PriceAud,
                        StockStatus,
                        StockQuantity,
                        Construction,
                        FinSetup,
                        LengthFeetInches,
                        Width,
                        Thickness,
                        VolumeLitres,
                        EstimatedShippingAud,
                        InventoryConfidenceScore,
                        LastCheckedUtc,
                        IsActive,
                        CreatedAtUtc,
                        UpdatedAtUtc
                    )
                    VALUES (
                        :retailer_id,
                        :brand_id,
                        NULL,
                        NULL,
                        :raw_title,
                        :normalised_title,
                        :product_url,
                        :image_url,
                        :price,
                        :stock_status,
                        NULL,
                        :construction,
                        :fin_setup,
                        :length,
                        :width,
                        :thickness,
                        :volume,
                        NULL,
                        :confidence,
                        GETUTCDATE(),
                        1,
                        GETUTCDATE(),
                        GETUTCDATE()
                    )
                """),
                insert_rows,
            )

    print("\nRetailer inventory import complete.")
    print(f"Retailers processed: {len(retailer_keys)}")
    print(f"Available inventory rows inserted: {len(insert_rows)}\n")


if __name__ == "__main__":
    main()