import os
import re
from urllib.parse import quote_plus

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text


load_dotenv()


def build_connection_string() -> str:

    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")
    driver = os.getenv(
        "SQL_DRIVER",
        "ODBC Driver 18 for SQL Server"
    )

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

    return (
        "mssql+pyodbc:///?odbc_connect="
        + quote_plus(odbc_string)
    )


engine = create_engine(
    build_connection_string(),
    pool_pre_ping=True,
    pool_recycle=180
)


app = FastAPI(
    title="Quivrr API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def clean_text(value):

    if value is None:
        return ""

    text_value = str(value).lower()
    text_value = text_value.replace("’", "'")
    text_value = text_value.replace("‘", "'")
    text_value = text_value.replace('"', "")
    text_value = re.sub(r"[^a-z0-9']+", " ", text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()

    return text_value


def model_family_name(model_name):

    model = clean_text(model_name)

    if not model:
        return ""

    parts = model.split()
    family_parts = []

    for part in parts:
        if re.search(r"\d", part):
            break

        family_parts.append(part)

    if family_parts:
        return " ".join(family_parts)

    return model


def text_contains_phrase(title, normalised_title, phrase):

    cleaned_phrase = clean_text(phrase)

    if not cleaned_phrase:
        return False

    combined_title = clean_text(
        f"{title or ''} {normalised_title or ''}"
    )

    pattern = (
        rf"(?<![a-z0-9])"
        rf"{re.escape(cleaned_phrase)}"
        rf"(?![a-z0-9])"
    )

    return re.search(pattern, combined_title) is not None


def model_family_matches(title, normalised_title, model_name):

    family_name = model_family_name(model_name)

    return text_contains_phrase(
        title,
        normalised_title,
        family_name
    )


def model_name_matches(title, normalised_title, model_name):

    if text_contains_phrase(
        title,
        normalised_title,
        model_name
    ):
        return True

    return model_family_matches(
        title,
        normalised_title,
        model_name
    )


def format_volume(value):

    if value is None:
        return None

    return float(value)


def format_size_label(row):

    volume = format_volume(row.VolumeLitres)

    if volume is None:
        volume_text = ""
    else:
        volume_text = f"{volume:g}L"

    return (
        f"{row.LengthFeetInches} x "
        f"{row.Width} x "
        f"{row.Thickness} / "
        f"{volume_text}"
    )


def format_price(value):

    if value is None:
        return None

    return float(value)


def retailer_result(row, result_type):

    return {
        "resultType": result_type,
        "inventoryId": row.InventoryId,
        "retailerName": row.RetailerName,
        "websiteUrl": row.WebsiteUrl,
        "retailerLogoUrl": row.LogoUrl,
        "title": row.RawProductTitle,
        "productUrl": row.ProductUrl,
        "imageUrl": row.ProductImageUrl,
        "priceAud": format_price(row.PriceAud),
        "stockStatus": row.StockStatus,
        "construction": row.Construction,
        "finSetup": row.FinSetup,
        "length": row.LengthFeetInches,
        "width": row.Width,
        "thickness": row.Thickness,
        "volumeLitres": format_volume(
            row.VolumeLitres
        )
    }


@app.get("/")
def root():

    return {
        "status": "online",
        "service": "quivrr-api"
    }


@app.get("/api/brands")
def get_brands():

    query = text("""
        SELECT
            BrandId,
            BrandName
        FROM dbo.Brands
        WHERE IsActive = 1
        ORDER BY BrandName
    """)

    with engine.connect() as connection:
        results = connection.execute(query)

        brands = [
            {
                "brandId": row.BrandId,
                "brandName": row.BrandName
            }
            for row in results
        ]

    return brands


@app.get("/api/models/{brand_id}")
def get_models(brand_id: int):

    query = text("""
        SELECT
            BoardModelId,
            ModelName
        FROM dbo.BoardModels
        WHERE BrandId = :brand_id
        AND IsActive = 1
        ORDER BY ModelName
    """)

    with engine.connect() as connection:
        results = connection.execute(
            query,
            {
                "brand_id": brand_id
            }
        )

        models = [
            {
                "modelId": row.BoardModelId,
                "modelName": row.ModelName
            }
            for row in results
        ]

    return models


@app.get("/api/constructions/{model_id}")
def get_constructions(model_id: int):

    query = text("""
        SELECT DISTINCT
            Construction
        FROM dbo.BoardSizes
        WHERE BoardModelId = :model_id
        AND Construction IS NOT NULL
        ORDER BY Construction
    """)

    with engine.connect() as connection:
        results = connection.execute(
            query,
            {
                "model_id": model_id
            }
        )

        constructions = [
            {
                "construction": row.Construction
            }
            for row in results
        ]

    return constructions


@app.get("/api/sizes/{model_id}/{construction}")
def get_sizes(
    model_id: int,
    construction: str
):

    query = text("""
        SELECT
            MIN(BoardSizeId) AS BoardSizeId,
            LengthFeetInches,
            Width,
            Thickness,
            VolumeLitres,
            Construction
        FROM dbo.BoardSizes
        WHERE BoardModelId = :model_id
        AND Construction = :construction
        GROUP BY
            LengthFeetInches,
            Width,
            Thickness,
            VolumeLitres,
            Construction
        ORDER BY
            VolumeLitres,
            LengthFeetInches,
            Width,
            Thickness
    """)

    with engine.connect() as connection:
        results = connection.execute(
            query,
            {
                "model_id": model_id,
                "construction": construction
            }
        )

        sizes = []

        for row in results:
            volume = format_volume(
                row.VolumeLitres
            )

            sizes.append({
                "boardSizeId": row.BoardSizeId,
                "label": format_size_label(row),
                "length": row.LengthFeetInches,
                "width": row.Width,
                "thickness": row.Thickness,
                "volumeLitres": volume,
                "construction": row.Construction
            })

    return sizes


@app.get("/api/search")
def search_inventory(boardSizeId: int):

    official_query = text("""
        SELECT
            bs.BoardSizeId,
            b.BrandName,
            bm.ModelName,
            bm.OfficialProductUrl,
            bs.LengthFeetInches,
            bs.Width,
            bs.Thickness,
            bs.VolumeLitres,
            bs.Construction,
            bs.FinSetup,
            bs.TailShape
        FROM dbo.BoardSizes bs
        INNER JOIN dbo.BoardModels bm
            ON bs.BoardModelId = bm.BoardModelId
        INNER JOIN dbo.Brands b
            ON bm.BrandId = b.BrandId
        WHERE bs.BoardSizeId = :board_size_id
    """)

    exact_query = text("""
        SELECT TOP 200
            ri.InventoryId,
            ri.RawProductTitle,
            ri.NormalisedProductTitle,
            ri.ProductUrl,
            ri.ProductImageUrl,
            ri.PriceAud,
            ri.StockStatus,
            ri.Construction,
            ri.FinSetup,
            ri.LengthFeetInches,
            ri.Width,
            ri.Thickness,
            ri.VolumeLitres,
            r.RetailerName,
            r.WebsiteUrl,
            r.LogoUrl,
            CASE
                WHEN ri.VolumeLitres IS NULL THEN NULL
                ELSE ABS(
                    CAST(ri.VolumeLitres AS float)
                    - CAST(:volume AS float)
                )
            END AS VolumeDelta
        FROM dbo.RetailerInventory ri
        INNER JOIN dbo.Retailers r
            ON ri.RetailerId = r.RetailerId
        WHERE ri.IsActive = 1
        AND (
            ri.StockStatus IS NULL
            OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN (
                'in stock',
                'instock',
                'available',
                'true'
            )
        )
        AND ri.LengthFeetInches = :length
        AND (
            ri.RawProductTitle LIKE :model_match
            OR ri.NormalisedProductTitle LIKE :model_match
            OR ri.RawProductTitle LIKE :model_family_match
            OR ri.NormalisedProductTitle LIKE :model_family_match
        )
        AND (
            ri.VolumeLitres IS NULL
            OR ABS(
                CAST(ri.VolumeLitres AS float)
                - CAST(:volume AS float)
            ) <= 0.75
        )
        ORDER BY
            CASE
                WHEN ri.VolumeLitres IS NULL THEN 1
                ELSE 0
            END,
            VolumeDelta ASC,
            ri.PriceAud ASC,
            r.RetailerName ASC
    """)

    close_query = text("""
        SELECT TOP 200
            ri.InventoryId,
            ri.RawProductTitle,
            ri.NormalisedProductTitle,
            ri.ProductUrl,
            ri.ProductImageUrl,
            ri.PriceAud,
            ri.StockStatus,
            ri.Construction,
            ri.FinSetup,
            ri.LengthFeetInches,
            ri.Width,
            ri.Thickness,
            ri.VolumeLitres,
            r.RetailerName,
            r.WebsiteUrl,
            r.LogoUrl,
            CASE
                WHEN ri.VolumeLitres IS NULL THEN NULL
                ELSE ABS(
                    CAST(ri.VolumeLitres AS float)
                    - CAST(:volume AS float)
                )
            END AS VolumeDelta
        FROM dbo.RetailerInventory ri
        INNER JOIN dbo.Retailers r
            ON ri.RetailerId = r.RetailerId
        WHERE ri.IsActive = 1
        AND (
            ri.StockStatus IS NULL
            OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN (
                'in stock',
                'instock',
                'available',
                'true'
            )
        )
        AND ri.LengthFeetInches = :length
        AND (
            ri.RawProductTitle LIKE :model_family_match
            OR ri.NormalisedProductTitle LIKE :model_family_match
        )
        AND (
            ri.VolumeLitres IS NULL
            OR ABS(
                CAST(ri.VolumeLitres AS float)
                - CAST(:volume AS float)
            ) <= 1.75
        )
        ORDER BY
            CASE
                WHEN ri.VolumeLitres IS NULL THEN 1
                ELSE 0
            END,
            VolumeDelta ASC,
            ri.PriceAud ASC,
            r.RetailerName ASC
    """)

    with engine.connect() as connection:
        official = connection.execute(
            official_query,
            {
                "board_size_id": boardSizeId
            }
        ).fetchone()

        if not official:
            return {
                "manufacturer": None,
                "exactRetailerMatches": [],
                "closeRetailerMatches": []
            }

        model_match = f"%{official.ModelName}%"
        model_family_match = f"%{model_family_name(official.ModelName)}%"

        official_result = {
            "resultType": "manufacturer",
            "brandName": official.BrandName,
            "modelName": official.ModelName,
            "productUrl": official.OfficialProductUrl,
            "label": format_size_label(official),
            "length": official.LengthFeetInches,
            "width": official.Width,
            "thickness": official.Thickness,
            "volumeLitres": format_volume(
                official.VolumeLitres
            ),
            "construction": official.Construction,
            "finSetup": official.FinSetup,
            "tailShape": official.TailShape
        }

        exact_results = connection.execute(
            exact_query,
            {
                "model_match": model_match,
                "model_family_match": model_family_match,
                "length": official.LengthFeetInches,
                "volume": official.VolumeLitres
            }
        )

        exact_matches = []

        for row in exact_results:
            if not model_name_matches(
                row.RawProductTitle,
                row.NormalisedProductTitle,
                official.ModelName
            ):
                continue

            exact_matches.append(
                retailer_result(
                    row,
                    "retailerExact"
                )
            )

            if len(exact_matches) >= 50:
                break

        exact_ids = {
            row["inventoryId"]
            for row in exact_matches
        }

        close_results = connection.execute(
            close_query,
            {
                "model_family_match": model_family_match,
                "length": official.LengthFeetInches,
                "volume": official.VolumeLitres
            }
        )

        close_matches = []

        for row in close_results:
            if row.InventoryId in exact_ids:
                continue

            if not model_family_matches(
                row.RawProductTitle,
                row.NormalisedProductTitle,
                official.ModelName
            ):
                continue

            item = retailer_result(
                row,
                "retailerClose"
            )

            item["volumeDelta"] = (
                float(row.VolumeDelta)
                if row.VolumeDelta is not None
                else None
            )

            close_matches.append(item)

            if len(close_matches) >= 50:
                break

    return {
        "manufacturer": official_result,
        "exactRetailerMatches": exact_matches,
        "closeRetailerMatches": close_matches
    }


@app.get("/api/test-db")
def test_database_connection():

    with engine.connect() as connection:
        result = connection.execute(
            text(
                "SELECT DB_NAME() AS database_name;"
            )
        )

        database_name = result.scalar()

    return {
        "status": "connected",
        "database": database_name
    }