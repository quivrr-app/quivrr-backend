import json
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text


load_dotenv()

BRAND_ID = 1
BRAND_NAME = "Channel Islands"
CATALOGUE_PATH = Path(
    "scrapers/brands/channel_islands/output/ci_master_catalogue_clean.json"
)


def build_connection_string():
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


@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(
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

    cleaned = str(value).strip()

    return cleaned or None


def load_catalogue():
    if not CATALOGUE_PATH.exists():
        raise FileNotFoundError(
            f"Missing catalogue file: {CATALOGUE_PATH}"
        )

    with CATALOGUE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("CI catalogue must be a list")

    return data


def build_models(catalogue):
    models = {}

    for item in catalogue:
        model_name = clean(item.get("model_name"))

        if not model_name:
            continue

        if model_name not in models:
            models[model_name] = {
                "brand_id": BRAND_ID,
                "model_name": model_name,
                "product_url": clean(item.get("product_url")),
                "is_active": True,
                "sizes": item.get("sizes") or [],
                "constructions": item.get("constructions") or ["PU"],
                "official_image_url": clean(item.get("official_image_url")),
            }

    return models


def build_size_rows(models, model_cache):
    size_rows = []
    seen = set()

    for model in models.values():
        model_name = model["model_name"]
        model_id = model_cache.get(model_name)

        if not model_id:
            continue

        constructions = model.get("constructions") or ["PU"]

        for size in model.get("sizes", []):
            length = clean(size.get("length"))
            width = clean(size.get("width"))
            thickness = clean(size.get("thickness"))
            volume = size.get("volume_litres")

            if not length or not width or not thickness:
                continue

            for construction in constructions:
                row_key = (
                    model_id,
                    length,
                    width,
                    thickness,
                    volume,
                    construction,
                )

                if row_key in seen:
                    continue

                seen.add(row_key)

                size_rows.append({
                    "model_id": model_id,
                    "length": length,
                    "width": width,
                    "thickness": thickness,
                    "volume": volume,
                    "construction": construction,
                    "fin_setup": None,
                    "tail_shape": None,
                })

    return size_rows


def insert_size_rows(connection, size_rows):
    if not size_rows:
        return

    connection.execute(
        text("""
            INSERT INTO dbo.BoardSizes (
                BoardModelId,
                LengthFeetInches,
                Width,
                Thickness,
                VolumeLitres,
                Construction,
                FinSetup,
                TailShape,
                IsStockSize,
                CreatedAtUtc
            )
            VALUES (
                :model_id,
                :length,
                :width,
                :thickness,
                :volume,
                :construction,
                :fin_setup,
                :tail_shape,
                1,
                GETUTCDATE()
            );
        """),
        size_rows
    )


def verify_brand(connection):
    row = connection.execute(
        text("""
            SELECT
                BrandId,
                BrandName
            FROM dbo.Brands
            WHERE BrandId = :brand_id;
        """),
        {
            "brand_id": BRAND_ID
        }
    ).fetchone()

    if not row:
        raise RuntimeError(
            f"BrandId {BRAND_ID} does not exist in dbo.Brands"
        )

    if row.BrandName != BRAND_NAME:
        print(
            f"Warning: BrandId {BRAND_ID} is named "
            f"'{row.BrandName}', expected '{BRAND_NAME}'"
        )


def main():
    print("")
    print("Importing Channel Islands catalogue into SQL...")
    print("")

    catalogue = load_catalogue()
    models = build_models(catalogue)

    print(f"Catalogue models loaded: {len(catalogue)}")
    print(f"Models prepared: {len(models)}")

    with engine.begin() as connection:
        verify_brand(connection)

        print("Cleaning existing Channel Islands catalogue...")

        connection.execute(
            text("""
                DELETE bs
                FROM dbo.BoardSizes bs
                INNER JOIN dbo.BoardModels bm
                    ON bs.BoardModelId = bm.BoardModelId
                WHERE bm.BrandId = :brand_id;
            """),
            {
                "brand_id": BRAND_ID
            }
        )

        connection.execute(
            text("""
                DELETE FROM dbo.BoardModels
                WHERE BrandId = :brand_id;
            """),
            {
                "brand_id": BRAND_ID
            }
        )

        print(f"Inserting models: {len(models)}")

        model_cache = {}

        for model in models.values():
            result = connection.execute(
                text("""
                    INSERT INTO dbo.BoardModels (
                        BrandId,
                        ModelName,
                        OfficialProductUrl,
                        OfficialImageUrl,
                        IsActive,
                        CreatedAtUtc
                    )
                    OUTPUT INSERTED.BoardModelId
                    VALUES (
                        :brand_id,
                        :model_name,
                        :product_url,
                        :official_image_url,
                        :is_active,
                        GETUTCDATE()
                    );
                """),
                {
                    "brand_id": model["brand_id"],
                    "model_name": model["model_name"],
                    "product_url": model["product_url"],
                    "official_image_url": model["official_image_url"],
                    "is_active": model["is_active"],
                }
            ).fetchone()

            model_cache[model["model_name"]] = result.BoardModelId

        size_rows = build_size_rows(
            models,
            model_cache
        )

        print(f"Batch inserting sizes: {len(size_rows)}")

        insert_size_rows(
            connection,
            size_rows
        )

    print(f"Models imported: {len(model_cache)}")
    print(f"Rows inserted: {len(size_rows)}")
    print("")
    print("Channel Islands import complete.")
    print("")


if __name__ == "__main__":
    main()
