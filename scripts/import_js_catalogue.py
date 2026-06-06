import json
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text


load_dotenv()

BRAND_ID = 4
CATALOGUE_PATH = Path("scrapers/brands/js/output/js_page_catalogue.json")
LEGACY_OVERRIDE_PATH = Path(
    "scrapers/brands/manual_catalogue_overrides/js_industries_legacy_models.json"
)


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

    cleaned = str(value).strip()

    return cleaned or None


def load_catalogue():
    with CATALOGUE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_legacy_overrides():
    if not LEGACY_OVERRIDE_PATH.exists():
        return []

    with LEGACY_OVERRIDE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        return []

    legacy_models = []

    for item in data:
        model_name = clean(item.get("model"))

        if not model_name:
            continue

        sizes = item.get("sizes")

        if not isinstance(sizes, list):
            sizes = []

        legacy_models.append({
            "brand_id": BRAND_ID,
            "model_name": model_name,
            "product_url": clean(item.get("product_url")),
            "status": clean(item.get("status")) or "legacy",
            "source": clean(item.get("source")) or "manual_override",
            "reason": clean(item.get("reason")),
            "is_active": bool(item.get("is_active", True)),
            "sizes": sizes,
        })

    return legacy_models


def build_catalogue_models(catalogue, legacy_overrides):
    models = {}

    for item in catalogue:
        model_name = clean(item.get("model"))

        if not model_name:
            continue

        if model_name not in models:
            models[model_name] = {
                "brand_id": BRAND_ID,
                "model_name": model_name,
                "product_url": clean(item.get("product_url")),
                "status": "current",
                "source": "manufacturer_catalogue",
                "reason": None,
                "is_active": True,
                "sizes": [],
            }

    for legacy_model in legacy_overrides:
        model_name = legacy_model["model_name"]

        if model_name in models:
            models[model_name]["status"] = legacy_model["status"]
            models[model_name]["source"] = legacy_model["source"]
            models[model_name]["reason"] = legacy_model["reason"]
            models[model_name]["is_active"] = legacy_model["is_active"]

            if legacy_model.get("product_url"):
                models[model_name]["product_url"] = legacy_model["product_url"]

            models[model_name]["sizes"] = legacy_model.get("sizes", [])
            continue

        models[model_name] = legacy_model

    return models


def build_catalogue_size_rows(catalogue, model_cache):
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
            "tail_shape": clean(item.get("tail_shape")),
        })

    return size_rows


def build_legacy_size_rows(legacy_overrides, model_cache):
    size_rows = []

    for legacy_model in legacy_overrides:
        model_name = legacy_model["model_name"]
        model_id = model_cache.get(model_name)

        if not model_id:
            continue

        for size in legacy_model.get("sizes", []):
            length = clean(size.get("length"))
            width = clean(size.get("width"))
            thickness = clean(size.get("thickness"))

            if not length or not width or not thickness:
                continue

            size_rows.append({
                "model_id": model_id,
                "length": length,
                "width": width,
                "thickness": thickness,
                "volume": size.get("volume_litres"),
                "construction": clean(size.get("construction")) or "PU",
                "fin_setup": clean(size.get("fin_system")),
                "tail_shape": clean(size.get("tail_shape")),
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


def main():
    print("")
    print("Importing JS page catalogue into SQL...")
    print("")

    catalogue = load_catalogue()
    legacy_overrides = load_legacy_overrides()
    models = build_catalogue_models(catalogue, legacy_overrides)

    print(f"Catalogue rows loaded: {len(catalogue)}")
    print(f"Legacy model overrides loaded: {len(legacy_overrides)}")
    print(f"Models prepared: {len(models)}")

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
                        :is_active,
                        GETUTCDATE()
                    );
                """),
                {
                    "brand_id": model["brand_id"],
                    "model_name": model["model_name"],
                    "product_url": model["product_url"],
                    "is_active": model["is_active"],
                }
            ).fetchone()

            model_cache[model["model_name"]] = result.BoardModelId

        catalogue_size_rows = build_catalogue_size_rows(
            catalogue,
            model_cache
        )

        legacy_size_rows = build_legacy_size_rows(
            legacy_overrides,
            model_cache
        )

        size_rows = catalogue_size_rows + legacy_size_rows

        print(f"Catalogue size rows: {len(catalogue_size_rows)}")
        print(f"Legacy size rows: {len(legacy_size_rows)}")
        print(f"Batch inserting sizes: {len(size_rows)}")

        insert_size_rows(connection, size_rows)

    print(f"Models imported: {len(model_cache)}")
    print(f"Rows inserted: {len(size_rows)}")
    print("")
    print("Import complete.")
    print("")


if __name__ == "__main__":
    main()
