import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


INPUT_FILE = Path("scrapers/manufacturers/availability/output/js_industries/js_au_manufacturer_inventory.json")


def normalise_js_construction(value):
    value = (value or "").strip()

    if value.upper() == "HYFI":
        return "HYFI 3.0"

    return value


def clean(value):
    if value is None:
        return None

    value = str(value).strip()
    return value or None


def get_engine():
    load_dotenv(dotenv_path=Path(".env"))

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

    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(cs)}")


def main():
    print("")
    print("Importing JS Industries AU manufacturer availability")
    print(f"Input: {INPUT_FILE}")

    rows = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    engine = get_engine()

    with engine.begin() as conn:
        brand_id = conn.execute(text("""
            SELECT BrandId
            FROM dbo.Brands
            WHERE BrandName = 'JS Industries'
        """)).scalar()

        if not brand_id:
            raise RuntimeError("JS Industries brand not found")

        conn.execute(text("""
            UPDATE dbo.ManufacturerInventory
            SET IsActive = 0,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE BrandId = :brand_id
              AND RegionCode = 'AU'
              AND AvailabilitySource = 'manufacturer_direct'
        """), {"brand_id": brand_id})

        inserted = 0

        for row in rows:
            model_name = clean(row.get("modelName"))
            length = clean(row.get("lengthFeetInches"))
            volume = row.get("volumeLitres")
            construction = normalise_js_construction(row.get("construction"))

            board_model_id = None
            board_size_id = None

            if model_name:
                board_model_id = conn.execute(text("""
                    SELECT TOP 1 BoardModelId
                    FROM dbo.BoardModels
                    WHERE BrandId = :brand_id
                      AND (
                          ModelName = :model_name
                          OR :model_name LIKE '%' + ModelName + '%'
                          OR ModelName LIKE '%' + :model_name + '%'
                      )
                    ORDER BY
                        CASE WHEN ModelName = :model_name THEN 0 ELSE 1 END,
                        LEN(ModelName) DESC
                """), {
                    "brand_id": brand_id,
                    "model_name": model_name,
                }).scalar()

            if board_model_id and length:
                board_size_id = conn.execute(text("""
                    SELECT TOP 1 BoardSizeId
                    FROM dbo.BoardSizes
                    WHERE BoardModelId = :board_model_id
                      AND LengthFeetInches = :length
                      AND (
                          :volume IS NULL
                          OR VolumeLitres IS NULL
                          OR ABS(CAST(VolumeLitres AS FLOAT) - CAST(:volume AS FLOAT)) <= 0.75
                      )
                      AND (
                          :width IS NULL
                          OR Width IS NULL
                          OR REPLACE(REPLACE(Width, '"', ''), ' ', '') = REPLACE(REPLACE(:width, '"', ''), ' ', '')
                      )
                      AND (
                          :thickness IS NULL
                          OR Thickness IS NULL
                          OR REPLACE(REPLACE(Thickness, '"', ''), ' ', '') = REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                      )
                      AND (
                          :construction IS NULL
                          OR Construction IS NULL
                          OR Construction = :construction
                          OR Construction LIKE '%' + :construction + '%'
                          OR :construction LIKE '%' + Construction + '%'
                      )
                    ORDER BY
                        CASE
                            WHEN :volume IS NOT NULL AND VolumeLitres IS NOT NULL
                            THEN ABS(CAST(VolumeLitres AS FLOAT) - CAST(:volume AS FLOAT))
                            ELSE 999
                        END,
                        CASE
                            WHEN :width IS NOT NULL AND Width IS NOT NULL THEN 0 ELSE 1
                        END,
                        CASE
                            WHEN :thickness IS NOT NULL AND Thickness IS NOT NULL THEN 0 ELSE 1
                        END
                """), {
                    "board_model_id": board_model_id,
                    "length": length,
                    "volume": volume,
                    "width": clean(row.get("width")),
                    "thickness": clean(row.get("thickness")),
                    "construction": construction,
                }).scalar()

            conn.execute(text("""
                INSERT INTO dbo.ManufacturerInventory (
                    BrandId,
                    BoardModelId,
                    BoardSizeId,
                    BrandName,
                    ModelName,
                    RawProductTitle,
                    NormalisedProductTitle,
                    ProductUrl,
                    ProductImageUrl,
                    LengthFeetInches,
                    Width,
                    Thickness,
                    VolumeLitres,
                    Construction,
                    FinSetup,
                    PriceAmount,
                    PriceCurrency,
                    StockStatus,
                    IsAvailable,
                    Source,
                    SourcePayload,
                    ScrapedAtUtc,
                    IsActive,
                    RegionCode,
                    AvailabilitySource
                )
                VALUES (
                    :brand_id,
                    :board_model_id,
                    :board_size_id,
                    :brand_name,
                    :model_name,
                    :raw_product_title,
                    :normalised_product_title,
                    :product_url,
                    :product_image_url,
                    :length,
                    :width,
                    :thickness,
                    :volume,
                    :construction,
                    :fin_setup,
                    :price_amount,
                    :price_currency,
                    :stock_status,
                    :is_available,
                    :source,
                    :source_payload,
                    SYSUTCDATETIME(),
                    1,
                    :region_code,
                    'manufacturer_direct'
                )
            """), {
                "brand_id": brand_id,
                "board_model_id": board_model_id,
                "board_size_id": board_size_id,
                "brand_name": clean(row.get("brandName")) or "JS Industries",
                "model_name": model_name,
                "raw_product_title": clean(row.get("rawProductTitle")),
                "normalised_product_title": clean(row.get("normalisedProductTitle")),
                "product_url": clean(row.get("productUrl")),
                "product_image_url": clean(row.get("productImageUrl")),
                "length": length,
                "width": clean(row.get("width")),
                "thickness": clean(row.get("thickness")),
                "volume": volume,
                "construction": construction,
                "fin_setup": clean(row.get("finSetup")),
                "price_amount": row.get("priceAmount"),
                "price_currency": clean(row.get("priceCurrency")) or "AUD",
                "stock_status": clean(row.get("stockStatus")),
                "is_available": 1 if row.get("isAvailable") else 0,
                "source": clean(row.get("source")),
                "source_payload": json.dumps(row.get("sourcePayload"), ensure_ascii=False),
                "region_code": clean(row.get("regionCode")) or "AU",
            })

            inserted += 1

        summary = conn.execute(text("""
            SELECT
                COUNT(*) AS TotalRows,
                SUM(CASE WHEN IsAvailable = 1 THEN 1 ELSE 0 END) AS AvailableRows,
                COUNT(BoardModelId) AS LinkedModelRows,
                COUNT(BoardSizeId) AS LinkedSizeRows
            FROM dbo.ManufacturerInventory
            WHERE BrandId = :brand_id
              AND RegionCode = 'AU'
              AND IsActive = 1
        """), {"brand_id": brand_id}).fetchone()

        print("")
        print("Import complete")
        print(f"Inserted rows: {inserted}")
        print(dict(summary._mapping))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"JS Industries manufacturer availability import failed: {exc}")
        sys.exit(1)
