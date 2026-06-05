import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

INPUT_PATH = Path("scrapers/manufacturers/availability/output/channel_islands/ci_au_manufacturer_inventory.json")


CI_MODEL_DISPLAY_NAMES = {
    "average-joe": "Average Joe",
    "better-everyday": "Better Everyday",
    "better-everyday-spinetek": "Better Everyday",
    "big-happy": "Big Happy",
    "black-and-white": "Black/White",
    "black-beauty": "Black Beauty",
    "bobby-quad": "Bobby Quad",
    "ci-2-pro": "CI 2.Pro",
    "ci-2-pro-spinetek": "CI 2.Pro",
    "ci-pro": "CI Pro",
    "ci-pro-step-up": "CI Pro Step Up",
    "ci-2-pro-step-up": "CI Pro Step Up",
    "ci-mid": "CI Mid",
    "ci-mid-twin": "CI Mid Twin",
    "dumpster-diver": "Dumpster Diver",
    "dumpster-diver-2": "Dumpster Diver 2",
    "dumpster-diver-2-spinetek": "Dumpster Diver 2",
    "febs-fish": "Feb's Fish",
    "feb-s-fish": "Feb's Fish",
    "fishbeard": "Fish Beard",
    "fish-beard": "Fish Beard",
    "fever": "Fever",
    "g-skate": "G Skate",
    "girabbit": "Girabbit",
    "goldie": "Goldie",
    "happy": "Happy",
    "happy-everyday": "Happy Everyday",
    "happy-everyday-spinetek": "Happy Everyday",
    "happy-everyday-fcsii": "Happy Everyday",
    "happy-traveler": "Happy Traveler",
    "happy-traveler-1": "Happy Traveler",
    "m23": "M23",
    "m-23": "M23",
    "mavs-gun": "Mavs Gun",
    "mikey-february-shorty": "Mikey February Shorty",
    "neckbeard": "The Neckbeard",
    "neckbeard-2": "Neckbeard 2",
    "neckbeard-3": "NeckBeard 3",
    "og-flyer": "OG Flyer",
    "og-flyer-ect-epoxy": "OG Flyer",
    "og-flyer-ect-epoxy-fcsii": "OG Flyer",
    "og-flyer-ect-epoxy-futures": "OG Flyer",
    "pod-mod": "Pod Mod",
    "pod-mod-1": "Pod Mod",
    "rocket-wide": "Rocket Wide",
    "rocket-wide-squash": "Rocket Wide Squash",
    "rook-15": "Rook 15",
    "sampler": "Sampler",
    "semi-pro-12": "Semi Pro 12",
    "solution": "The Solution",
    "solution-spinetek": "The Solution",
    "the-solution": "The Solution",
    "taco-grinder": "Taco Grinder",
    "taco-grinder-1": "Taco Grinder",
    "the-black-beauty": "Black Beauty",
    "the-proton": "The Proton",
    "the-water-hog": "Waterhog",
    "tph-single-fin-1": "Tri Plane Hull",
    "twin-fin": "Twin Fin",
    "twin-pin": "Twin Pin",
    "two-happy": "Two Happy",
    "ultra-joe": "Ultra Joe",
    "ultra-joe-1": "Ultra Joe",
    "waterhog": "Waterhog",
}


MODEL_SUFFIXES = [
    "-spinetek-futures",
    "-spinetek-fcsii",
    "-spine-tek-futures",
    "-spine-tek-fcsii",
    "-spine-tek",
    "-spinetek",
    "-ect-epoxy-futures",
    "-ect-epoxy-fcsii",
    "-ect-epoxy",
    "-futures",
    "-fcsii",
]


def now_utc():
    return datetime.now(timezone.utc)


def clean(value):
    if value is None:
        return None

    value = str(value).replace("\u2019", "'").replace("\u2018", "'").strip()

    return value or None


def normalise_slug(value):
    value = clean(value)

    if not value:
        return None

    return value.lower().strip()


def resolve_ci_display_name(value):
    slug = normalise_slug(value)

    if not slug:
        return None

    if slug in CI_MODEL_DISPLAY_NAMES:
        return CI_MODEL_DISPLAY_NAMES[slug]

    for suffix in MODEL_SUFFIXES:
        if slug.endswith(suffix):
            base_slug = slug[: -len(suffix)]

            if base_slug in CI_MODEL_DISPLAY_NAMES:
                return CI_MODEL_DISPLAY_NAMES[base_slug]

            slug = base_slug
            break

    if slug in CI_MODEL_DISPLAY_NAMES:
        return CI_MODEL_DISPLAY_NAMES[slug]

    return slug.replace("-", " ").title()


def get_connection():
    load_dotenv()

    connection_string = (
        f"DRIVER={{{os.getenv('SQL_DRIVER', 'ODBC Driver 18 for SQL Server')}}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USERNAME')};"
        f"PWD={os.getenv('SQL_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    for attempt in range(1, 6):
        try:
            return pyodbc.connect(connection_string, timeout=30)
        except Exception:
            if attempt == 5:
                raise
            time.sleep(10)


def execute_with_retry(cursor, sql, *params, attempts=5, delay_seconds=10):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            if not params:
                return cursor.execute(sql)

            if len(params) == 1 and isinstance(params[0], (list, tuple)):
                return cursor.execute(sql, params[0])

            return cursor.execute(sql, params)
        except Exception as exc:
            last_error = exc

            if attempt == attempts:
                raise

            time.sleep(delay_seconds)

    raise last_error


def get_columns(cursor):
    execute_with_retry(cursor, """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'ManufacturerInventory'
    """)

    return {row[0] for row in cursor.fetchall()}


def get_brand_id(cursor):
    execute_with_retry(cursor, """
        SELECT BrandId
        FROM dbo.Brands
        WHERE BrandName = ?
    """, "Channel Islands")

    row = cursor.fetchone()

    return row[0] if row else None


def resolve_catalogue(cursor, brand_id, row):
    model_name = resolve_ci_display_name(row.get("modelName"))
    length = clean(row.get("length"))
    construction = clean(row.get("construction"))

    resolved = {
        "BoardModelId": None,
        "BoardSizeId": None,
        "Width": row.get("width"),
        "Thickness": row.get("thickness"),
        "VolumeLitres": row.get("volumeLitres"),
        "CanonicalModelName": model_name,
    }

    if not brand_id or not model_name or not length:
        return resolved

    execute_with_retry(cursor, """
        SELECT BoardModelId, ModelName
        FROM dbo.BoardModels
        WHERE BrandId = ?
          AND LOWER(LTRIM(RTRIM(ModelName))) = LOWER(LTRIM(RTRIM(?)))
    """, brand_id, model_name)

    model = cursor.fetchone()

    if not model:
        return resolved

    board_model_id = model[0]
    resolved["BoardModelId"] = board_model_id

    execute_with_retry(cursor, """
        SELECT TOP 1
            BoardSizeId,
            Width,
            Thickness,
            VolumeLitres,
            Construction
        FROM dbo.BoardSizes
        WHERE BoardModelId = ?
          AND LengthFeetInches = ?
          AND (
              ? IS NULL
              OR Construction IS NULL
              OR LOWER(LTRIM(RTRIM(Construction))) = LOWER(LTRIM(RTRIM(?)))
          )
        ORDER BY
            CASE
                WHEN ? IS NOT NULL
                 AND Construction IS NOT NULL
                 AND LOWER(LTRIM(RTRIM(Construction))) = LOWER(LTRIM(RTRIM(?)))
                THEN 0
                ELSE 1
            END,
            BoardSizeId
    """, board_model_id, length, construction, construction, construction, construction)

    size = cursor.fetchone()

    if size:
        resolved["BoardSizeId"] = size[0]
        resolved["Width"] = clean(size[1])
        resolved["Thickness"] = clean(size[2])
        resolved["VolumeLitres"] = float(size[3]) if size[3] is not None else None

    return resolved


def insert_row(cursor, columns, row, resolved, brand_id):
    values = {
        "BrandId": brand_id,
        "BrandName": "Channel Islands",
        "ModelName": resolved.get("CanonicalModelName") or clean(row.get("modelName")),
        "BoardModelId": resolved.get("BoardModelId"),
        "BoardSizeId": resolved.get("BoardSizeId"),
        "LengthFeetInches": clean(row.get("length")),
        "Width": resolved.get("Width"),
        "Thickness": resolved.get("Thickness"),
        "VolumeLitres": resolved.get("VolumeLitres"),
        "Construction": clean(row.get("construction")),
        "FinSetup": clean(row.get("finSetup")),
        "PriceAmount": row.get("priceAmount"),
        "PriceCurrency": clean(row.get("priceCurrency")) or "AUD",
        "StockStatus": clean(row.get("stockStatus")),
        "IsAvailable": 1 if row.get("isAvailable") else 0,
        "ProductUrl": clean(row.get("productUrl")),
        "ProductImageUrl": clean(row.get("productImageUrl")),
        "AvailabilitySource": "manufacturer_direct",
        "RegionCode": "AU",
        "RawProductTitle": clean(row.get("rawProductTitle")),
        "NormalisedProductTitle": clean(row.get("modelName")),
        "Source": clean(row.get("source")) or "ci_au_products_json_paginated",
        "ScrapedAtUtc": clean(row.get("scrapedAtUtc")),
        "UpdatedAtUtc": now_utc(),
        "IsActive": 1,
    }

    insert_cols = [
        column
        for column in values.keys()
        if column in columns
    ]

    placeholders = ", ".join(["?"] * len(insert_cols))
    col_sql = ", ".join(insert_cols)

    execute_with_retry(
        cursor,
        f"INSERT INTO dbo.ManufacturerInventory ({col_sql}) VALUES ({placeholders})",
        [values[column] for column in insert_cols],
    )


def main():
    print("Importing Channel Islands AU manufacturer availability")
    print(f"Input: {INPUT_PATH}")

    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    conn = get_connection()
    cursor = conn.cursor()

    columns = get_columns(cursor)
    brand_id = get_brand_id(cursor)

    execute_with_retry(cursor, """
        DELETE FROM dbo.ManufacturerInventory
        WHERE BrandName = 'Channel Islands'
          AND RegionCode = 'AU'
          AND AvailabilitySource = 'manufacturer_direct'
    """)

    inserted = 0
    linked_models = 0
    linked_sizes = 0

    for row in data:
        resolved = resolve_catalogue(cursor, brand_id, row)

        if resolved.get("BoardModelId") is not None:
            linked_models += 1

        if resolved.get("BoardSizeId") is not None:
            linked_sizes += 1

        insert_row(cursor, columns, row, resolved, brand_id)
        inserted += 1

    conn.commit()
    conn.close()

    print("")
    print("Import complete")
    print(f"Inserted rows: {inserted}")
    print({
        "TotalRows": inserted,
        "AvailableRows": sum(1 for row in data if row.get("isAvailable")),
        "LinkedModelRows": linked_models,
        "LinkedSizeRows": linked_sizes,
    })


if __name__ == "__main__":
    main()
