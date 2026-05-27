import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from scrapers.brands.scrape_js_industries import fetch_page, extract_board_models, JS_MODELS_URL
from scrapers.brands.normalise_js_models import normalise_js_models

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


def get_brand_id(connection) -> int:
    result = connection.execute(
        text("SELECT BrandId FROM dbo.Brands WHERE BrandName = :brand_name"),
        {"brand_name": "JS Industries"}
    ).scalar()

    if result is None:
        raise RuntimeError("JS Industries not found in dbo.Brands.")

    return int(result)


def upsert_board_model(connection, brand_id: int, model: dict) -> None:
    category = "Surfboard"

    if model["is_softboard"]:
        category = "Softboard"

    if model["is_youth"]:
        category = "Youth Surfboard"

    if model["is_easy_rider"]:
        category = "Easy Rider"

    query = text("""
        IF EXISTS (
            SELECT 1
            FROM dbo.BoardModels
            WHERE BrandId = :brand_id
              AND ModelName = :model_name
              AND OfficialProductUrl = :official_product_url
        )
        BEGIN
            UPDATE dbo.BoardModels
            SET
                BoardCategory = :board_category,
                OfficialProductUrl = :official_product_url,
                IsActive = 1,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE BrandId = :brand_id
              AND ModelName = :model_name
              AND OfficialProductUrl = :official_product_url
        END
        ELSE
        BEGIN
            INSERT INTO dbo.BoardModels (
                BrandId,
                ModelName,
                BoardCategory,
                OfficialProductUrl,
                IsActive
            )
            VALUES (
                :brand_id,
                :model_name,
                :board_category,
                :official_product_url,
                1
            )
        END
    """)

    connection.execute(query, {
        "brand_id": brand_id,
        "model_name": model["model_name"],
        "board_category": category,
        "official_product_url": model["official_product_url"]
    })


def main() -> None:
    html = fetch_page(JS_MODELS_URL)
    raw_models = extract_board_models(html)
    normalised_models = normalise_js_models(raw_models)

    engine = create_engine(build_connection_string())

    with engine.begin() as connection:
        brand_id = get_brand_id(connection)

        for model in normalised_models:
            upsert_board_model(connection, brand_id, model)

    print(f"Saved {len(normalised_models)} JS Industries catalogue records into dbo.BoardModels.")


if __name__ == "__main__":
    main()