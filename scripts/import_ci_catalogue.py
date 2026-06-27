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
        "Connection Timeout=60;"
        "ConnectRetryCount=3;"
        "ConnectRetryInterval=5;"
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


def begin_with_retry(max_attempts=4, delay_seconds=8):
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            return engine.begin()
        except Exception as exc:
            last_error = exc
            print(
                f"SQL connection attempt {attempt}/{max_attempts} failed: {exc}"
            )

            if attempt < max_attempts:
                time.sleep(delay_seconds)

    raise last_error


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
                "description": clean(item.get("description")),
                "board_category": clean(item.get("board_category")),
            }
            continue

        existing = models[model_name]
        existing["product_url"] = existing["product_url"] or clean(item.get("product_url"))
        existing["official_image_url"] = existing["official_image_url"] or clean(item.get("official_image_url"))
        existing["description"] = existing["description"] or clean(item.get("description"))
        existing["board_category"] = existing["board_category"] or clean(item.get("board_category"))

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

    with begin_with_retry() as connection:
        verify_brand(connection)

        print("Syncing existing Channel Islands catalogue...")

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
            brand_name=BRAND_NAME,
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

        size_rows = build_size_rows(
            models,
            model_cache
        )
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

        print(f"Batch inserting new sizes: {len(new_size_rows)}")

        insert_size_rows(
            connection,
            new_size_rows
        )

    print(f"Models imported: {len(model_cache)}")
    print(f"Rows inserted: {len(new_size_rows)}")
    print("")
    print("Channel Islands import complete.")
    print("")


if __name__ == "__main__":
    main()
