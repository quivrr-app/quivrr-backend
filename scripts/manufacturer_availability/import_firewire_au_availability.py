import json
import os
import time
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

load_dotenv()

INPUT_PATH = Path("scrapers/manufacturers/availability/output/firewire/firewire_au_manufacturer_inventory.json")

BRAND_NAME = "Firewire"
REGION_CODE = "AU"
AVAILABILITY_SOURCE = "manufacturer_direct"

connection_string = (
    f"DRIVER={{{os.getenv('SQL_DRIVER', 'ODBC Driver 18 for SQL Server')}}};"
    f"SERVER={os.getenv('SQL_SERVER')};"
    f"DATABASE={os.getenv('SQL_DATABASE')};"
    f"UID={os.getenv('SQL_USERNAME')};"
    f"PWD={os.getenv('SQL_PASSWORD')};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
)


def connect():
    for attempt in range(1, 6):
        try:
            return pyodbc.connect(connection_string, timeout=30)
        except Exception:
            if attempt == 5:
                raise
            time.sleep(10)


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return (
        value
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )


def to_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def get_columns(cursor):
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'ManufacturerInventory'
    """)

    return {row[0] for row in cursor.fetchall()}


def find_brand_id(cursor):
    cursor.execute("""
        SELECT TOP 1 BrandId
        FROM dbo.Brands
        WHERE BrandName = ?
    """, BRAND_NAME)

    row = cursor.fetchone()

    if not row:
        raise RuntimeError(f"Could not find BrandId for {BRAND_NAME}")

    return row[0]


def find_board_model_id(cursor, model_name):
    if not model_name:
        return None

    cursor.execute("""
        SELECT TOP 1
            bm.BoardModelId
        FROM dbo.BoardModels bm
        JOIN dbo.Brands b
            ON bm.BrandId = b.BrandId
        WHERE b.BrandName = ?
          AND LOWER(bm.ModelName) = LOWER(?)
    """, BRAND_NAME, model_name)

    row = cursor.fetchone()

    return row[0] if row else None


def find_board_size_id(cursor, board_model_id, item):
    if not board_model_id:
        return None

    length = clean(item.get("lengthFeetInches"))
    width = clean(item.get("width"))
    thickness = clean(item.get("thickness"))
    volume = to_float(item.get("volumeLitres"))
    construction = clean(item.get("construction"))

    params = [board_model_id, length]

    query = """
        SELECT
            BoardSizeId,
            Construction
        FROM dbo.BoardSizes
        WHERE BoardModelId = ?
          AND LengthFeetInches = ?
    """

    if width:
        query += " AND Width = ?"
        params.append(width)

    if thickness:
        query += " AND Thickness = ?"
        params.append(thickness)

    if volume is not None:
        query += " AND VolumeLitres IS NOT NULL AND ABS(CAST(VolumeLitres AS float) - ?) <= 0.15"
        params.append(volume)

    query += " ORDER BY BoardSizeId"

    cursor.execute(query, params)

    rows = cursor.fetchall()

    if not rows:
        return None

    def normalise_firewire_construction(value):
        value = clean(value) or ""
        value = value.lower()
        value = value.replace("-", " ")
        value = value.replace(".", " ")
        value = " ".join(value.split())

        aliases = {
            "ibolic": "i bolic",
            "i bolic": "i bolic",
            "i bolic 2 0": "i bolic",
            "ibolic 2 0": "i bolic",
            "i bolic volcanic": "i bolic volcanic",
            "ibolic volcanic": "i bolic volcanic",
            "volcanic": "volcanic",
            "helium": "helium",
            "g flex": "g flex",
            "gflex": "g flex",
            "proflex": "proflex",
        }

        return aliases.get(value, value)

    target_construction = normalise_firewire_construction(construction)

    exact_matches = [
        row for row in rows
        if normalise_firewire_construction(row.Construction) == target_construction
    ]

    if exact_matches:
        return exact_matches[0].BoardSizeId

    if len(rows) == 1:
        return rows[0].BoardSizeId

    return None


def insert_row(cursor, columns, item, brand_id, board_model_id, board_size_id):
    values = {
        "BrandId": brand_id,
        "BrandName": BRAND_NAME,
        "ModelName": clean(item.get("modelName")),
        "BoardModelId": board_model_id,
        "BoardSizeId": board_size_id,
        "LengthFeetInches": clean(item.get("lengthFeetInches")),
        "Width": clean(item.get("width")),
        "Thickness": clean(item.get("thickness")),
        "VolumeLitres": to_float(item.get("volumeLitres")),
        "Construction": clean(item.get("construction")),
        "FinSetup": clean(item.get("finSetup")),
        "TailShape": clean(item.get("tailShape")),
        "ProductUrl": clean(item.get("productUrl")),
        "ProductImageUrl": clean(item.get("productImageUrl")),
        "PriceAmount": to_float(item.get("priceAmount")),
        "PriceCurrency": clean(item.get("priceCurrency")) or "AUD",
        "StockStatus": clean(item.get("stockStatus")) or "available",
        "IsAvailable": 1 if item.get("isAvailable") else 0,
        "AvailabilitySource": AVAILABILITY_SOURCE,
        "RegionCode": REGION_CODE,
        "SourceProductId": clean(item.get("sourceProductId")),
        "SourceVariantId": clean(item.get("sourceVariantId")),
        "SourceVariantTitle": clean(item.get("sourceVariantTitle")),
        "IsActive": 1,
    }

    usable = {
        key: value
        for key, value in values.items()
        if key in columns
    }

    column_sql = ", ".join(f"[{key}]" for key in usable.keys())
    placeholder_sql = ", ".join("?" for _ in usable)
    params = list(usable.values())

    cursor.execute(
        f"""
        INSERT INTO dbo.ManufacturerInventory
            ({column_sql})
        VALUES
            ({placeholder_sql})
        """,
        params
    )


def main():
    if not INPUT_PATH.exists():
        raise SystemExit(f"Missing input file: {INPUT_PATH}")

    rows = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    conn = connect()
    cursor = conn.cursor()

    columns = get_columns(cursor)

    print("Importing Firewire AU manufacturer availability")
    print(f"Input: {INPUT_PATH}")
    print(f"Rows: {len(rows)}")

    if "BrandName" not in columns:
        raise SystemExit("dbo.ManufacturerInventory does not contain BrandName")

    delete_conditions = ["BrandName = ?"]
    delete_params = [BRAND_NAME]

    if "AvailabilitySource" in columns:
        delete_conditions.append("AvailabilitySource = ?")
        delete_params.append(AVAILABILITY_SOURCE)

    if "RegionCode" in columns:
        delete_conditions.append("RegionCode = ?")
        delete_params.append(REGION_CODE)

    cursor.execute(
        f"""
        DELETE FROM dbo.ManufacturerInventory
        WHERE {" AND ".join(delete_conditions)}
        """,
        delete_params
    )

    inserted = 0
    linked_models = 0
    linked_sizes = 0

    brand_id = find_brand_id(cursor)

    model_cache = {}
    size_cache = {}

    for item in rows:
        model_name = clean(item.get("modelName"))

        if model_name not in model_cache:
            model_cache[model_name] = find_board_model_id(cursor, model_name)

        board_model_id = model_cache[model_name]

        if board_model_id:
            linked_models += 1

        size_key = (
            board_model_id,
            clean(item.get("lengthFeetInches")),
            clean(item.get("width")),
            clean(item.get("thickness")),
            item.get("volumeLitres"),
            clean(item.get("construction")),
        )

        if size_key not in size_cache:
            size_cache[size_key] = find_board_size_id(cursor, board_model_id, item)

        board_size_id = size_cache[size_key]

        if board_size_id:
            linked_sizes += 1

        for attempt in range(1, 6):
            try:
                insert_row(
                    cursor,
                    columns,
                    item,
                    brand_id,
                    board_model_id,
                    board_size_id
                )
                break

            except pyodbc.OperationalError as exc:
                print(f"SQL retry {attempt}/5 for {model_name}: {exc}")

                if attempt == 5:
                    raise

                try:
                    conn.close()
                except Exception:
                    pass

                time.sleep(5)

                conn = connect()
                cursor = conn.cursor()
                columns = get_columns(cursor)

        inserted += 1

    conn.commit()

    print("")
    print("Firewire AU manufacturer availability import complete")
    print(f"Inserted rows: {inserted}")
    print({
        "TotalRows": len(rows),
        "LinkedModelRows": linked_models,
        "LinkedSizeRows": linked_sizes,
    })

    conn.close()


if __name__ == "__main__":
    main()
