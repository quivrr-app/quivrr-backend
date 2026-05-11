import os
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


engine = create_engine(build_connection_string())


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

            volume = (
                float(row.VolumeLitres)
                if row.VolumeLitres
                else None
            )

            label = (
                f"{row.LengthFeetInches} x "
                f"{row.Width} x "
                f"{row.Thickness} / "
                f"{volume:g}L"
            )

            sizes.append({
                "boardSizeId": row.BoardSizeId,
                "label": label,
                "length": row.LengthFeetInches,
                "width": row.Width,
                "thickness": row.Thickness,
                "volumeLitres": volume,
                "construction": row.Construction
            })

    return sizes


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