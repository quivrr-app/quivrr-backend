import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app import engine

INPUT_PATH = Path("scrapers/manufacturers/availability/output/js_industries/js_id_manufacturer_inventory.json")
BRAND_NAME = "JS Industries"
REGION_CODE = "ID"
AVAILABILITY_SOURCE = "manufacturer_direct"

def norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()

def columns(conn, table):
    rows = conn.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table
    """), {"table": table}).fetchall()
    return {r.COLUMN_NAME for r in rows}

def get_brand_id(conn):
    row = conn.execute(text("""
        SELECT BrandId
        FROM dbo.Brands
        WHERE BrandName = :brand
    """), {"brand": BRAND_NAME}).fetchone()

    if not row:
        raise RuntimeError(f"Brand not found: {BRAND_NAME}")

    return row.BrandId

def find_model_id(conn, brand_id, model_name):
    row = conn.execute(text("""
        SELECT TOP 1 BoardModelId
        FROM dbo.BoardModels
        WHERE BrandId = :brand_id
          AND LOWER(ModelName) = LOWER(:model_name)
        ORDER BY BoardModelId
    """), {"brand_id": brand_id, "model_name": model_name}).fetchone()

    if row:
        return row.BoardModelId

    row = conn.execute(text("""
        SELECT TOP 1 BoardModelId
        FROM dbo.BoardModels
        WHERE BrandId = :brand_id
          AND (
              LOWER(ModelName) LIKE LOWER(:model_like)
              OR LOWER(:model_name) LIKE '%' + LOWER(ModelName) + '%'
          )
        ORDER BY LEN(ModelName) DESC, BoardModelId
    """), {
        "brand_id": brand_id,
        "model_name": model_name,
        "model_like": f"%{model_name}%"
    }).fetchone()

    return row.BoardModelId if row else None

def find_size_id(conn, model_id, row):
    if not model_id:
        return None

    params = {
        "model_id": model_id,
        "length": row.get("lengthFeetInches"),
        "construction": row.get("construction"),
        "volume": row.get("volumeLitres"),
    }

    result = conn.execute(text("""
        SELECT TOP 1 BoardSizeId
        FROM dbo.BoardSizes
        WHERE BoardModelId = :model_id
          AND LengthFeetInches = :length
          AND (
              :construction IS NULL
              OR Construction IS NULL
              OR LOWER(Construction) = LOWER(:construction)
              OR (:construction = 'PU' AND LOWER(Construction) IN ('pu', 'pe'))
          )
          AND (
              :volume IS NULL
              OR VolumeLitres IS NULL
              OR ABS(CAST(VolumeLitres AS float) - CAST(:volume AS float)) <= 1.0
          )
        ORDER BY
          CASE WHEN LOWER(ISNULL(Construction, '')) = LOWER(ISNULL(:construction, '')) THEN 0 ELSE 1 END,
          CASE WHEN VolumeLitres IS NULL OR :volume IS NULL THEN 1 ELSE ABS(CAST(VolumeLitres AS float) - CAST(:volume AS float)) END
    """), params).fetchone()

    return result.BoardSizeId if result else None

def add_if_exists(payload, table_cols, column, value):
    if column in table_cols:
        payload[column] = value

def main():
    rows = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()

    if not rows:
        raise RuntimeError("No rows found in JS Indonesia MFA output")

    with engine.begin() as conn:
        mi_cols = columns(conn, "ManufacturerInventory")
        brand_id = get_brand_id(conn)

        deleted = conn.execute(text("""
            DELETE FROM dbo.ManufacturerInventory
            WHERE BrandId = :brand_id
              AND RegionCode = :region_code
              AND AvailabilitySource = :availability_source
        """), {
            "brand_id": brand_id,
            "region_code": REGION_CODE,
            "availability_source": AVAILABILITY_SOURCE,
        }).rowcount

        inserted = 0
        linked_models = 0
        linked_sizes = 0

        for row in rows:
            model_id = find_model_id(conn, brand_id, row.get("modelName"))
            size_id = find_size_id(conn, model_id, row)

            if model_id:
                linked_models += 1
            if size_id:
                linked_sizes += 1

            payload = {}

            add_if_exists(payload, mi_cols, "BrandId", brand_id)
            add_if_exists(payload, mi_cols, "BoardModelId", model_id)
            add_if_exists(payload, mi_cols, "BoardSizeId", size_id)
            add_if_exists(payload, mi_cols, "BrandName", BRAND_NAME)
            add_if_exists(payload, mi_cols, "ModelName", row.get("modelName"))
            add_if_exists(payload, mi_cols, "RawProductTitle", row.get("rawProductTitle"))
            add_if_exists(payload, mi_cols, "ProductUrl", row.get("productUrl"))
            add_if_exists(payload, mi_cols, "ProductImageUrl", row.get("productImageUrl"))
            add_if_exists(payload, mi_cols, "PriceAmount", row.get("priceAmount"))
            add_if_exists(payload, mi_cols, "PriceCurrency", row.get("priceCurrency"))
            add_if_exists(payload, mi_cols, "StockStatus", row.get("stockStatus"))
            add_if_exists(payload, mi_cols, "IsAvailable", 1 if row.get("isAvailable") else 0)
            add_if_exists(payload, mi_cols, "RegionCode", REGION_CODE)
            add_if_exists(payload, mi_cols, "AvailabilitySource", AVAILABILITY_SOURCE)
            add_if_exists(payload, mi_cols, "LengthFeetInches", row.get("lengthFeetInches"))
            add_if_exists(payload, mi_cols, "Width", row.get("width"))
            add_if_exists(payload, mi_cols, "Thickness", row.get("thickness"))
            add_if_exists(payload, mi_cols, "VolumeLitres", row.get("volumeLitres"))
            add_if_exists(payload, mi_cols, "Construction", row.get("construction"))
            add_if_exists(payload, mi_cols, "FinSetup", row.get("finSetup"))
            add_if_exists(payload, mi_cols, "TailShape", row.get("tailShape"))
            add_if_exists(payload, mi_cols, "SourceProductId", row.get("sourceProductId"))
            add_if_exists(payload, mi_cols, "SourceVariantId", row.get("sourceVariantId"))
            add_if_exists(payload, mi_cols, "SourceVariantTitle", row.get("sourceVariantTitle"))
            add_if_exists(payload, mi_cols, "LastCheckedUtc", row.get("lastCheckedUtc") or now)
            add_if_exists(payload, mi_cols, "CreatedAtUtc", now)
            add_if_exists(payload, mi_cols, "UpdatedAtUtc", now)
            add_if_exists(payload, mi_cols, "IsActive", 1)

            names = ", ".join(payload.keys())
            binds = ", ".join(f":{k}" for k in payload)

            conn.execute(text(f"""
                INSERT INTO dbo.ManufacturerInventory ({names})
                VALUES ({binds})
            """), payload)

            inserted += 1

    print("JS Indonesia MFA import complete")
    print("Deleted scoped ID rows:", deleted)
    print("Inserted:", inserted)
    print("LinkedModel:", linked_models)
    print("LinkedSize:", linked_sizes)

if __name__ == "__main__":
    main()
