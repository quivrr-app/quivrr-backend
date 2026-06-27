import json
import os
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import bindparam, create_engine, event, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.import_brand_catalogue_common import validate_missing_model_deactivation

load_dotenv()

BRAND_ID = 4
CATALOGUE_PATH = Path("scrapers/brands/js/output/js_page_catalogue.json")
LEGACY_OVERRIDE_PATH = Path(
    "scrapers/brands/manual_catalogue_overrides/js_industries_legacy_models.json"
)
MAX_SQL_ATTEMPTS = 4
SQL_RETRY_DELAYS_SECONDS = [0, 5, 10, 20]


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
        "Connection Timeout=60;"
        "ConnectRetryCount=3;"
        "ConnectRetryInterval=5;"
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
            "official_image_url": clean(item.get("official_image_url")),
            "description": clean(item.get("description")),
            "board_category": clean(item.get("board_category")),
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
                "official_image_url": clean(item.get("official_image_url")),
                "description": clean(item.get("description")),
                "board_category": clean(item.get("board_category")),
                "status": "current",
                "source": "manufacturer_catalogue",
                "reason": None,
                "is_active": True,
                "sizes": [],
            }
            continue

        existing = models[model_name]
        existing["product_url"] = existing["product_url"] or clean(item.get("product_url"))
        existing["official_image_url"] = existing["official_image_url"] or clean(item.get("official_image_url"))
        existing["description"] = existing["description"] or clean(item.get("description"))
        existing["board_category"] = existing["board_category"] or clean(item.get("board_category"))

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


def normalise_volume(value):
    if value in (None, ""):
        return None

    try:
        normalised = Decimal(str(value)).normalize()
    except (InvalidOperation, ValueError):
        text_value = str(value).strip()
        return text_value or None

    rendered = format(normalised, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def size_signature(row):
    return (
        int(row["model_id"]),
        clean(row.get("length")) or "",
        clean(row.get("width")) or "",
        clean(row.get("thickness")) or "",
        normalise_volume(row.get("volume")),
        clean(row.get("construction")) or "",
        clean(row.get("fin_setup")) or "",
        clean(row.get("tail_shape")) or "",
    )


def existing_size_signature(row):
    return (
        int(row.BoardModelId),
        clean(row.LengthFeetInches) or "",
        clean(row.Width) or "",
        clean(row.Thickness) or "",
        normalise_volume(row.VolumeLitres),
        clean(row.Construction) or "",
        clean(row.FinSetup) or "",
        clean(row.TailShape) or "",
    )


def partition_new_size_rows(existing_rows, incoming_rows):
    existing_signatures = {existing_size_signature(row) for row in existing_rows}
    rows_to_insert = []

    for row in incoming_rows:
        signature = size_signature(row)
        if signature in existing_signatures:
            continue
        existing_signatures.add(signature)
        rows_to_insert.append(row)

    return rows_to_insert


def run_import_transaction(models, catalogue, legacy_overrides):
    with engine.begin() as connection:
        print("Syncing existing JS catalogue...")

        existing_models = connection.execute(
            text("""
                SELECT BoardModelId, ModelName
                FROM dbo.BoardModels
                WHERE BrandId = :brand_id;
            """),
            {"brand_id": BRAND_ID},
        ).fetchall()
        existing_model_ids_by_name = {
            clean(row.ModelName): int(row.BoardModelId)
            for row in existing_models
            if clean(row.ModelName)
        }

        print(f"Syncing models: {len(models)}")

        model_cache = {}

        for model in models.values():
            model_name = model["model_name"]
            existing_model_id = existing_model_ids_by_name.get(model_name)

            if existing_model_id is not None:
                connection.execute(
                    text("""
                        UPDATE dbo.BoardModels
                        SET OfficialProductUrl = COALESCE(:product_url, OfficialProductUrl),
                            OfficialImageUrl = COALESCE(:official_image_url, OfficialImageUrl),
                            Description = COALESCE(:description, Description),
                            BoardCategory = COALESCE(:board_category, BoardCategory),
                            IsActive = :is_active,
                            UpdatedAtUtc = GETUTCDATE()
                        WHERE BoardModelId = :model_id;
                    """),
                    {
                        "model_id": existing_model_id,
                        "product_url": model["product_url"],
                        "official_image_url": model["official_image_url"],
                        "description": model["description"],
                        "board_category": model["board_category"],
                        "is_active": model["is_active"],
                    },
                )
                model_cache[model_name] = existing_model_id
                continue

            result = connection.execute(
                text("""
                    INSERT INTO dbo.BoardModels (
                        BrandId,
                        ModelName,
                        OfficialProductUrl,
                        OfficialImageUrl,
                        Description,
                        BoardCategory,
                        IsActive,
                        CreatedAtUtc
                    )
                    OUTPUT INSERTED.BoardModelId
                    VALUES (
                        :brand_id,
                        :model_name,
                        :product_url,
                        :official_image_url,
                        :description,
                        :board_category,
                        :is_active,
                        GETUTCDATE()
                    );
                """),
                {
                    "brand_id": model["brand_id"],
                    "model_name": model_name,
                    "product_url": model["product_url"],
                    "official_image_url": model["official_image_url"],
                    "description": model["description"],
                    "board_category": model["board_category"],
                    "is_active": model["is_active"],
                }
            ).fetchone()

            model_cache[model_name] = result.BoardModelId

        missing_model_names = validate_missing_model_deactivation(
            brand_name="JS Industries",
            existing_model_names=existing_model_ids_by_name.keys(),
            incoming_model_names=model_cache.keys(),
        )
        if missing_model_names:
            connection.execute(
                text("""
                    UPDATE dbo.BoardModels
                    SET IsActive = 0,
                        UpdatedAtUtc = GETUTCDATE()
                    WHERE BrandId = :brand_id
                      AND ModelName IN :model_names;
                """).bindparams(bindparam("model_names", expanding=True)),
                {
                    "brand_id": BRAND_ID,
                    "model_names": missing_model_names,
                },
            )

        catalogue_size_rows = build_catalogue_size_rows(
            catalogue,
            model_cache
        )

        legacy_size_rows = build_legacy_size_rows(
            legacy_overrides,
            model_cache
        )

        size_rows = catalogue_size_rows + legacy_size_rows
        existing_sizes = connection.execute(
            text("""
                SELECT
                    bs.BoardSizeId,
                    bs.BoardModelId,
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
                WHERE bm.BrandId = :brand_id;
            """),
            {"brand_id": BRAND_ID},
        ).fetchall()
        new_size_rows = partition_new_size_rows(existing_sizes, size_rows)

        print(f"Catalogue size rows: {len(catalogue_size_rows)}")
        print(f"Legacy size rows: {len(legacy_size_rows)}")
        print(f"Batch inserting new sizes: {len(new_size_rows)}")

        insert_size_rows(connection, new_size_rows)

    return model_cache, new_size_rows


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

    last_error = None

    for attempt in range(1, MAX_SQL_ATTEMPTS + 1):
        delay = SQL_RETRY_DELAYS_SECONDS[attempt - 1]

        if delay:
            print(f"Waiting {delay} seconds before SQL retry")

        try:
            if delay:
                time.sleep(delay)

            print(f"SQL import attempt {attempt} of {MAX_SQL_ATTEMPTS}")
            model_cache, new_size_rows = run_import_transaction(
                models,
                catalogue,
                legacy_overrides,
            )
            break
        except Exception as exc:
            last_error = exc
            print("")
            print(f"SQL import attempt {attempt} failed")
            print(str(exc))
            print("")

            if attempt == MAX_SQL_ATTEMPTS:
                raise

    if last_error and "model_cache" not in locals():
        raise last_error

    print(f"Models imported: {len(model_cache)}")
    print(f"Rows inserted: {len(new_size_rows)}")
    print("")
    print("Import complete.")
    print("")


if __name__ == "__main__":
    main()
