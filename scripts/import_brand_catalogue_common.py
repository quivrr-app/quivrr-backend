import json
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text


load_dotenv()


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
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if executemany:
        cursor.fast_executemany = True


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def load_catalogue(path):
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise RuntimeError(f"Catalogue must be a list: {path}")

    return data


def get_or_create_brand(connection, brand_name):
    row = connection.execute(
        text("""
            SELECT BrandId
            FROM dbo.Brands
            WHERE BrandName = :brand_name;
        """),
        {"brand_name": brand_name},
    ).fetchone()

    if row:
        return row.BrandId

    inserted = connection.execute(
        text("""
            INSERT INTO dbo.Brands (
                BrandName,
                IsActive,
                CreatedAtUtc
            )
            OUTPUT INSERTED.BrandId
            VALUES (
                :brand_name,
                1,
                GETUTCDATE()
            );
        """),
        {"brand_name": brand_name},
    ).fetchone()

    return inserted.BrandId


def build_models(catalogue):
    models = {}

    for item in catalogue:
        model_name = clean(item.get("model") or item.get("model_name"))

        if not model_name:
            continue

        if model_name not in models:
            models[model_name] = {
                "model_name": model_name,
                "model_family": clean(item.get("model_family") or item.get("model_name")) or model_name,
                "board_category": clean(item.get("board_category")),
                "official_product_url": clean(item.get("official_product_url")),
                "official_image_url": clean(item.get("official_image_url")),
                "is_active": bool(item.get("is_active", True)),
            }

    return models


def build_size_rows(catalogue, model_cache):
    rows = []

    for item in catalogue:
        model_name = clean(item.get("model") or item.get("model_name"))
        model_id = model_cache.get(model_name)

        if not model_id:
            continue

        length = clean(item.get("length") or item.get("length_feet_inches"))
        volume = item.get("volume_litres")

        if not length:
            continue

        rows.append({
            "model_id": model_id,
            "length": length,
            "width": clean(item.get("width")),
            "thickness": clean(item.get("thickness")),
            "volume": volume,
            "construction": clean(item.get("construction")),
            "fin_setup": clean(item.get("fin_system") or item.get("fin_setup")),
            "tail_shape": clean(item.get("tail_shape")),
        })

    return rows


def import_catalogue(brand_name, catalogue_path):
    print("")
    print(f"Importing {brand_name} catalogue into SQL")
    print(f"Input: {catalogue_path}")
    print("")

    catalogue = load_catalogue(catalogue_path)
    models = build_models(catalogue)

    print(f"Catalogue rows loaded: {len(catalogue)}")
    print(f"Models prepared: {len(models)}")

    with engine.begin() as connection:
        brand_id = get_or_create_brand(connection, brand_name)

        print(f"BrandId: {brand_id}")
        print(f"Cleaning existing {brand_name} catalogue")

        connection.execute(
            text("""
                DELETE bs
                FROM dbo.BoardSizes bs
                INNER JOIN dbo.BoardModels bm
                    ON bs.BoardModelId = bm.BoardModelId
                WHERE bm.BrandId = :brand_id;
            """),
            {"brand_id": brand_id},
        )

        connection.execute(
            text("""
                DELETE FROM dbo.BoardModels
                WHERE BrandId = :brand_id;
            """),
            {"brand_id": brand_id},
        )

        model_cache = {}

        for model in models.values():
            result = connection.execute(
                text("""
                    INSERT INTO dbo.BoardModels (
                        BrandId,
                        ModelName,
                        ModelFamily,
                        BoardCategory,
                        OfficialProductUrl,
                        OfficialImageUrl,
                        IsActive,
                        CreatedAtUtc
                    )
                    OUTPUT INSERTED.BoardModelId
                    VALUES (
                        :brand_id,
                        :model_name,
                        :model_family,
                        :board_category,
                        :official_product_url,
                        :official_image_url,
                        :is_active,
                        GETUTCDATE()
                    );
                """),
                {
                    "brand_id": brand_id,
                    "model_name": model["model_name"],
                    "model_family": model["model_family"],
                    "board_category": model["board_category"],
                    "official_product_url": model["official_product_url"],
                    "official_image_url": model["official_image_url"],
                    "is_active": model["is_active"],
                },
            ).fetchone()

            model_cache[model["model_name"]] = result.BoardModelId

        size_rows = build_size_rows(catalogue, model_cache)

        print(f"Batch inserting sizes: {len(size_rows)}")

        if size_rows:
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
                size_rows,
            )

    print(f"Models imported: {len(model_cache)}")
    print(f"Rows inserted: {len(size_rows)}")
    print("Import complete")
    print("")
