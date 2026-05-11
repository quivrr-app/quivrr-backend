import json
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text


load_dotenv()

BRAND_ID = 4
CATALOGUE_PATH = "./scrapers/brands/output/js_page_catalogue.json"


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

    return str(value).strip()


def main():
    print("\nImporting JS page catalogue into SQL...\n")

    with open(CATALOGUE_PATH, "r", encoding="utf-8") as file:
        catalogue = json.load(file)

    print(f"Catalogue rows loaded: {len(catalogue)}")

    models = {}

    for item in catalogue:
        model_name = clean(item.get("model"))

        if not model_name:
            continue

        if model_name not in models:
            models[model_name] = {
                "brand_id": BRAND_ID,
                "model_name": model_name,
                "product_url": clean(item.get("product_url"))
            }

    with engine.begin() as connection:
        print("Cleaning existing JS catalogue...")

        connection.execute(
            text("""
                DELETE bs
                FROM dbo.BoardSizes bs
                INNER JOIN dbo.BoardModels bm
                    ON bs.BoardModelId = bm.BoardModelId
                WHERE bm.BrandId = :brand_id;
            """),
            {"brand_id": BRAND_ID}
        )

        connection.execute(
            text("""
                DELETE FROM dbo.BoardModels
                WHERE BrandId = :brand_id;
            """),
            {"brand_id": BRAND_ID}
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
                        IsActive,
                        CreatedAtUtc
                    )
                    OUTPUT INSERTED.BoardModelId
                    VALUES (
                        :brand_id,
                        :model_name,
                        :product_url,
                        1,
                        GETUTCDATE()
                    );
                """),
                model
            ).fetchone()

            model_cache[model["model_name"]] = result.BoardModelId

        size_rows = []

        for item in catalogue:
            model_name = clean(item.get("model"))

            if not model_name or model_name not in model_cache:
                continue

            size_rows.append({
                "model_id": model_cache[model_name],
                "length": clean(item.get("length")),
                "width": clean(item.get("width")),
                "thickness": clean(item.get("thickness")),
                "volume": item.get("volume_litres"),
                "construction": clean(item.get("construction")),
                "fin_setup": clean(item.get("fin_system")),
                "tail_shape": clean(item.get("tail_shape"))
            })

        print(f"Batch inserting sizes: {len(size_rows)}")

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

    print(f"Models imported: {len(model_cache)}")
    print(f"Rows inserted: {len(size_rows)}")
    print("\nImport complete.\n")


if __name__ == "__main__":
    main()