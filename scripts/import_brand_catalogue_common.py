import json
import os
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import bindparam, create_engine, event, text
from sqlalchemy.exc import OperationalError


load_dotenv()


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
        "Connection Timeout=30;"
        "ConnectRetryCount=3;"
        "ConnectRetryInterval=5;"
    )

    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_string)


engine = create_engine(
    build_connection_string(),
    pool_pre_ping=True,
    pool_recycle=1800,
)


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


def get_default_brand_url(brand_name):
    if brand_name == "Misfit Shapes":
        return "https://misfitshapes.com"

    normalised = (
        brand_name.lower()
        .replace(" ", "")
        .replace("industries", "")
        .replace("surfboards", "")
    )

    return f"https://{normalised}.com"


def get_or_create_brand(connection, brand_name):
    official_website_url = get_default_brand_url(brand_name)

    row = connection.execute(
        text("""
            SELECT BrandId
            FROM dbo.Brands
            WHERE BrandName = :brand_name;
        """),
        {
            "brand_name": brand_name,
        },
    ).fetchone()

    if row:
        return row.BrandId

    inserted = connection.execute(
        text("""
            INSERT INTO dbo.Brands (
                BrandName,
                OfficialWebsiteUrl,
                IsActive,
                CreatedAtUtc
            )
            OUTPUT INSERTED.BrandId
            VALUES (
                :brand_name,
                :official_website_url,
                1,
                GETUTCDATE()
            );
        """),
        {
            "brand_name": brand_name,
            "official_website_url": official_website_url,
        },
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
                "description": clean(item.get("description")),
                "is_active": bool(item.get("is_active", True)),
            }
            continue

        existing = models[model_name]
        existing["model_family"] = existing["model_family"] or clean(item.get("model_family") or item.get("model_name")) or model_name
        existing["board_category"] = existing["board_category"] or clean(item.get("board_category"))
        existing["official_product_url"] = existing["official_product_url"] or clean(item.get("official_product_url"))
        existing["official_image_url"] = existing["official_image_url"] or clean(item.get("official_image_url"))
        existing["description"] = existing["description"] or clean(item.get("description"))
        existing["is_active"] = existing["is_active"] and bool(item.get("is_active", True))

    return models


def validate_missing_model_deactivation(
    *,
    brand_name,
    existing_model_names,
    incoming_model_names,
    max_missing_without_override=5,
    max_drop_ratio=0.2,
    min_existing_for_ratio_guard=10,
):
    existing = {clean(name) for name in existing_model_names if clean(name)}
    incoming = {clean(name) for name in incoming_model_names if clean(name)}

    if not existing:
        return []

    missing = sorted(existing - incoming)

    if not missing:
        return []

    allow_override = os.getenv("ALLOW_CATALOGUE_MODEL_DEACTIVATION", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    missing_ratio = len(missing) / max(len(existing), 1)
    exceeds_guard = (
        len(missing) > max_missing_without_override
        or (
            len(existing) >= min_existing_for_ratio_guard
            and missing_ratio > max_drop_ratio
        )
    )

    if exceeds_guard and not allow_override:
        sample = ", ".join(missing[:10])
        raise RuntimeError(
            f"{brand_name} catalogue regression guard blocked deactivation of "
            f"{len(missing)} models ({missing_ratio:.0%} of active models). "
            f"Sample missing models: {sample}. "
            "Set ALLOW_CATALOGUE_MODEL_DEACTIVATION=1 only for an explicitly reviewed cleanup."
        )

    return missing


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


def run_import_transaction(brand_name, catalogue, models):
    with engine.begin() as connection:
        brand_id = get_or_create_brand(connection, brand_name)

        print(f"BrandId: {brand_id}")
        print(f"Syncing existing {brand_name} catalogue")

        existing_models = connection.execute(
            text("""
                SELECT BoardModelId, ModelName
                FROM dbo.BoardModels
                WHERE BrandId = :brand_id;
            """),
            {"brand_id": brand_id},
        ).fetchall()
        existing_model_ids_by_name = {
            clean(row.ModelName): int(row.BoardModelId)
            for row in existing_models
            if clean(row.ModelName)
        }

        model_cache = {}

        for model in models.values():
            model_name = model["model_name"]
            existing_model_id = existing_model_ids_by_name.get(model_name)

            if existing_model_id is not None:
                connection.execute(
                    text("""
                        UPDATE dbo.BoardModels
                        SET ModelFamily = COALESCE(:model_family, ModelFamily),
                            BoardCategory = COALESCE(:board_category, BoardCategory),
                            OfficialProductUrl = COALESCE(:official_product_url, OfficialProductUrl),
                            OfficialImageUrl = COALESCE(:official_image_url, OfficialImageUrl),
                            Description = COALESCE(:description, Description),
                            IsActive = :is_active,
                            UpdatedAtUtc = GETUTCDATE()
                        WHERE BoardModelId = :model_id;
                    """),
                    {
                        "model_id": existing_model_id,
                        "model_family": model["model_family"],
                        "board_category": model["board_category"],
                        "official_product_url": model["official_product_url"],
                        "official_image_url": model["official_image_url"],
                        "description": model["description"],
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
                        ModelFamily,
                        BoardCategory,
                        OfficialProductUrl,
                        OfficialImageUrl,
                        Description,
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
                        :description,
                        :is_active,
                        GETUTCDATE()
                    );
                """),
                {
                    "brand_id": brand_id,
                    "model_name": model_name,
                    "model_family": model["model_family"],
                    "board_category": model["board_category"],
                    "official_product_url": model["official_product_url"],
                    "official_image_url": model["official_image_url"],
                    "description": model["description"],
                    "is_active": model["is_active"],
                },
            ).fetchone()

            model_cache[model_name] = result.BoardModelId

        missing_model_names = validate_missing_model_deactivation(
            brand_name=brand_name,
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
                    "brand_id": brand_id,
                    "model_names": missing_model_names,
                },
            )

        size_rows = build_size_rows(catalogue, model_cache)
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
            {"brand_id": brand_id},
        ).fetchall()
        new_size_rows = partition_new_size_rows(existing_sizes, size_rows)

        print(f"Batch inserting new sizes: {len(new_size_rows)}")

        if new_size_rows:
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
                new_size_rows,
            )

    return model_cache, new_size_rows


def import_catalogue(brand_name, catalogue_path):
    print("")
    print(f"Importing {brand_name} catalogue into SQL")
    print(f"Input: {catalogue_path}")
    print("")

    catalogue = load_catalogue(catalogue_path)
    models = build_models(catalogue)

    print(f"Catalogue rows loaded: {len(catalogue)}")
    print(f"Models prepared: {len(models)}")

    last_error = None

    for attempt in range(1, MAX_SQL_ATTEMPTS + 1):
        delay = SQL_RETRY_DELAYS_SECONDS[attempt - 1]

        if delay:
            print(f"Waiting {delay} seconds before SQL retry")
            time.sleep(delay)

        try:
            print(f"SQL import attempt {attempt} of {MAX_SQL_ATTEMPTS}")

            model_cache, size_rows = run_import_transaction(
                brand_name,
                catalogue,
                models,
            )

            print(f"Models imported: {len(model_cache)}")
            print(f"Rows inserted: {len(size_rows)}")
            print("Import complete")
            print("")
            return

        except OperationalError as exc:
            last_error = exc

            print("")
            print(f"SQL operational error on attempt {attempt}")
            print(str(exc))
            print("")

            if attempt == MAX_SQL_ATTEMPTS:
                raise

        except Exception:
            raise

    if last_error:
        raise last_error
