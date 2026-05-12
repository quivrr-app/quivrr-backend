import json
import os
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text


load_dotenv()

INPUT_FILE = "scrapers/products/output/normalised_surfboards.json"


def build_connection_string():
    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")

    odbc_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_string)


engine = create_engine(build_connection_string())


@event.listens_for(engine, "before_cursor_execute")
def enable_fast_executemany(
    conn,
    cursor,
    statement,
    parameters,
    context,
    executemany
):
    if executemany:
        cursor.fast_executemany = True


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def money(value):
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

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        inventory = json.load(file)

    available_inventory = [
        item for item in inventory
        if item.get("available") is True
    ]

    print(f"Rows loaded: {len(inventory)}")
    print(f"Available rows selected: {len(available_inventory)}")

    retailer_keys = {}

    for item in available_inventory:
        retailer_name = clean(item.get("retailer"))
        website = clean(item.get("website"))

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

        rows = []

        for item in available_inventory:
            retailer_name = clean(item.get("retailer"))

            if not retailer_name:
                continue

            retailer_id = existing_retailers.get(
                retailer_name.lower()
            )

            if retailer_id is None:
                continue

            raw_brand = clean(item.get("brand")) or clean(item.get("vendor"))

            brand_id = None

            if raw_brand:
                brand_id = brands.get(raw_brand.lower())

            rows.append({
                "retailer_id": retailer_id,
                "brand_id": brand_id,
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
                "volume": item.get("volume_litres"),
                "confidence": item.get("surfboard_confidence"),
            })

        print(f"Batch inserting available inventory rows: {len(rows)}")

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
            rows,
        )

    print("\nRetailer inventory import complete.")
    print(f"Retailers processed: {len(retailer_keys)}")
    print(f"Available inventory rows inserted: {len(rows)}\n")


if __name__ == "__main__":
    main()