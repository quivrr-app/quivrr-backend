
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import pyodbc
from dotenv import load_dotenv

BRAND_NAME = "Chemistry Surfboards"
INPUT_PATH = Path("scrapers/manufacturers/availability/output/chemistry/chemistry_au_manufacturer_inventory.json")

def now_utc():
    return datetime.now(timezone.utc)

def clean(value):
    if value is None:
        return None
    value = str(value).replace("\u2019", "'").replace("\u2018", "'").strip()
    return value or None

def get_connection():
    load_dotenv()

    connection_string = (
        f"DRIVER={{{os.getenv('SQL_DRIVER', 'ODBC Driver 18 for SQL Server')}}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USERNAME')};"
        f"PWD={os.getenv('SQL_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    for attempt in range(1, 6):
        try:
            return pyodbc.connect(connection_string, timeout=30)
        except Exception:
            if attempt == 5:
                raise
            time.sleep(10)

def get_columns(cursor):
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'ManufacturerInventory'
    """)
    return {row[0] for row in cursor.fetchall()}

def get_brand_id(cursor):
    cursor.execute("""
        SELECT BrandId
        FROM dbo.Brands
        WHERE BrandName = ?
    """, BRAND_NAME)

    row = cursor.fetchone()
    return row[0] if row else None

MODEL_MAP = {
    "b-side": "B Side",
    "b-side-ex-team": "B Side",
    "pantera-rosa": "Chemistry Pantera Rosa Surfboard",
    "summertime-pt-2": "Summertime Pt 2",
    "the-23": "Chemistry The 23 Surfboard",
    "the-zen-4": "Zen 4",
    "the-zen-4-1": "Zen 4 1",
    "the-zen-4-stock": "Zen 4",
}

def resolve_catalogue(cursor, brand_id, row):
    raw_model_name = clean(row.get("modelName"))
    model_name = MODEL_MAP.get(raw_model_name, raw_model_name)
    length = clean(row.get("length"))
    construction = clean(row.get("construction"))

    resolved = {
        "BoardModelId": None,
        "BoardSizeId": None,
        "Width": row.get("width"),
        "Thickness": row.get("thickness"),
        "VolumeLitres": row.get("volumeLitres"),
    }

    if not brand_id or not model_name:
        return resolved

    cursor.execute("""
        SELECT BoardModelId
        FROM dbo.BoardModels
        WHERE BrandId = ?
          AND LOWER(ModelName) = LOWER(?)
    """, brand_id, model_name)

    model = cursor.fetchone()

    if not model:
        return resolved

    board_model_id = model[0]
    resolved["BoardModelId"] = board_model_id

    if not length:
        return resolved

    cursor.execute("""
        SELECT TOP 1
            BoardSizeId,
            Width,
            Thickness,
            VolumeLitres
        FROM dbo.BoardSizes
        WHERE BoardModelId = ?
          AND LengthFeetInches = ?
          AND (
              ? IS NULL
              OR Construction IS NULL
              OR LOWER(LTRIM(RTRIM(Construction))) = LOWER(LTRIM(RTRIM(?)))
          )
        ORDER BY BoardSizeId
    """, board_model_id, length, construction, construction)

    size = cursor.fetchone()

    if size:
        resolved["BoardSizeId"] = size[0]
        resolved["Width"] = clean(size[1])
        resolved["Thickness"] = clean(size[2])
        resolved["VolumeLitres"] = float(size[3]) if size[3] is not None else None

    return resolved

def insert_row(cursor, columns, row, resolved, brand_id):
    values = {
        "BrandId": brand_id,
        "BrandName": BRAND_NAME,
        "ModelName": clean(row.get("modelName")),
        "BoardModelId": resolved.get("BoardModelId"),
        "BoardSizeId": resolved.get("BoardSizeId"),
        "LengthFeetInches": clean(row.get("length")),
        "Width": resolved.get("Width"),
        "Thickness": resolved.get("Thickness"),
        "VolumeLitres": resolved.get("VolumeLitres"),
        "Construction": clean(row.get("construction")),
        "FinSetup": clean(row.get("finSetup")),
        "PriceAmount": row.get("priceAmount"),
        "PriceCurrency": clean(row.get("priceCurrency")) or "AUD",
        "StockStatus": clean(row.get("stockStatus")),
        "IsAvailable": 1 if row.get("isAvailable") else 0,
        "ProductUrl": clean(row.get("productUrl")),
        "ProductImageUrl": clean(row.get("productImageUrl")),
        "AvailabilitySource": "manufacturer_direct",
        "RegionCode": "AU",
        "RawProductTitle": clean(row.get("rawProductTitle")),
        "Source": clean(row.get("source")) or "chemistry_au_products_json",
        "ScrapedAtUtc": clean(row.get("scrapedAtUtc")),
        "UpdatedAtUtc": now_utc(),
        "IsActive": 1,
    }

    insert_cols = [column for column in values.keys() if column in columns]
    placeholders = ", ".join(["?"] * len(insert_cols))
    col_sql = ", ".join(insert_cols)

    cursor.execute(
        f"INSERT INTO dbo.ManufacturerInventory ({col_sql}) VALUES ({placeholders})",
        [values[column] for column in insert_cols],
    )

def main():
    print("Importing Chemistry AU manufacturer availability")

    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    conn = get_connection()
    cursor = conn.cursor()
    columns = get_columns(cursor)
    brand_id = get_brand_id(cursor)

    if brand_id is None:
        raise RuntimeError("Chemistry Surfboards brand not found")

    cursor.execute("""
        DELETE FROM dbo.ManufacturerInventory
        WHERE BrandName = ?
          AND RegionCode = 'AU'
          AND AvailabilitySource = 'manufacturer_direct'
    """, BRAND_NAME)

    inserted = 0
    linked_models = 0
    linked_sizes = 0

    for row in data:
        resolved = resolve_catalogue(cursor, brand_id, row)

        if resolved.get("BoardModelId") is not None:
            linked_models += 1

        if resolved.get("BoardSizeId") is not None:
            linked_sizes += 1

        insert_row(cursor, columns, row, resolved, brand_id)
        inserted += 1

    conn.commit()
    conn.close()

    print("")
    print("Import complete")
    print(f"Inserted rows: {inserted}")
    print({
        "TotalRows": inserted,
        "AvailableRows": sum(1 for row in data if row.get("isAvailable")),
        "LinkedModelRows": linked_models,
        "LinkedSizeRows": linked_sizes,
    })

if __name__ == "__main__":
    main()
