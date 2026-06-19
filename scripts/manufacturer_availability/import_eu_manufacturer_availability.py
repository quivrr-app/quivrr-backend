from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.europe.import_eu_retailer_inventory import (  # noqa: E402
    build_engine,
    connect_with_retry,
    load_board_sizes,
    model_key,
    select_size_candidate,
)

REGION = "EU"
SOURCE = "manufacturer_direct"
CHUNK_SIZE = 500
FILES = list(
    Path("scrapers/manufacturers/availability").glob(
        "*/output/*_eu_manufacturer_inventory.json"
    )
)


def clean(value):
    return str(value or "").strip()


def load_rows():
    rows = []
    for path in FILES:
        rows.extend(json.loads(path.read_text(encoding="utf-8")))
    for index, row in enumerate(rows):
        if row.get("regionCode") != REGION:
            raise RuntimeError(f"Unsafe row {index}: RegionCode must be EU")
        if row.get("availabilitySource") != SOURCE:
            raise RuntimeError(f"Unsafe row {index}: invalid AvailabilitySource")
        if row.get("priceAmount") is not None and row.get("priceCurrency") != "EUR":
            raise RuntimeError(f"Unsafe row {index}: priced rows must use EUR")
    return rows


def region_counts(conn):
    return {
        clean(row.RegionCode) or "<NULL>": int(row.InventoryRows)
        for row in conn.execute(text("""
            SELECT RegionCode, COUNT(*) AS InventoryRows
            FROM dbo.ManufacturerInventory
            GROUP BY RegionCode
        """))
    }


def catalogue(conn):
    brands = {
        row.BrandName: int(row.BrandId)
        for row in conn.execute(text("SELECT BrandId, BrandName FROM dbo.Brands"))
    }
    models = defaultdict(lambda: defaultdict(list))
    for row in conn.execute(text("""
        SELECT BoardModelId, BrandId, ModelName FROM dbo.BoardModels
    """)):
        models[int(row.BrandId)][model_key(row.ModelName)].append(int(row.BoardModelId))
    return brands, models, load_board_sizes(conn)


def prepare_rows(conn, rows):
    brands, models, sizes = catalogue(conn)
    prepared = []
    for row in rows:
        brand_id = brands.get(row["brandName"])
        if brand_id is None:
            raise RuntimeError(f"Canonical brand missing: {row['brandName']}")
        matches = models[brand_id].get(model_key(row.get("modelName")), [])
        model_id = matches[0] if len(matches) == 1 else None
        size = select_size_candidate(
            {
                "lengthFeetInches": row.get("lengthFeetInches"),
                "volumeLitres": row.get("volumeLitres"),
            },
            model_id,
            sizes,
        ) if model_id else None
        prepared.append((row, brand_id, model_id, size["boardSizeId"] if size else None))
    return prepared


def make_payload(row, brand_id, model_id, size_id, columns):
    values = {
        "BrandId": brand_id,
        "BoardModelId": model_id,
        "BoardSizeId": size_id,
        "BrandName": row["brandName"],
        "ModelName": row.get("modelName"),
        "RawProductTitle": row.get("rawProductTitle"),
        "ProductUrl": row.get("productUrl"),
        "ProductImageUrl": row.get("productImageUrl"),
        "LengthFeetInches": row.get("lengthFeetInches"),
        "Width": row.get("width"),
        "Thickness": row.get("thickness"),
        "VolumeLitres": row.get("volumeLitres"),
        "Construction": row.get("construction"),
        "FinSetup": row.get("finSetup"),
        "PriceAmount": row.get("priceAmount"),
        "PriceCurrency": "EUR",
        "StockStatus": row.get("stockStatus") or "available",
        "IsAvailable": 1 if row.get("isAvailable") else 0,
        "Source": SOURCE,
        "SourcePayload": json.dumps(row, ensure_ascii=False),
        "IsActive": 1,
        "RegionCode": REGION,
        "AvailabilitySource": SOURCE,
    }
    return {key: value for key, value in values.items() if key in columns}


def import_brand(engine, brand, rows):
    started = time.perf_counter()
    with connect_with_retry(engine) as conn:
        transaction = conn.begin()
        try:
            protected_before = region_counts(conn)
            columns = {
                row.COLUMN_NAME for row in conn.execute(text("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='ManufacturerInventory'
                """))
            }
            brand_id = rows[0][1]
            deleted = conn.execute(text("""
                DELETE FROM dbo.ManufacturerInventory
                WHERE BrandId = :brand_id
                  AND RegionCode = 'EU'
                  AND AvailabilitySource = 'manufacturer_direct'
            """), {"brand_id": brand_id}).rowcount

            payloads = [make_payload(*item, columns) for item in rows]
            names = list(payloads[0])
            statement = text(
                "INSERT INTO dbo.ManufacturerInventory ("
                + ",".join(f"[{name}]" for name in names)
                + ") VALUES ("
                + ",".join(f":{name}" for name in names)
                + ")"
            )
            inserted = 0
            for offset in range(0, len(payloads), CHUNK_SIZE):
                chunk = payloads[offset:offset + CHUNK_SIZE]
                conn.execute(statement, chunk)  # SQLAlchemy executemany
                inserted += len(chunk)

            invalid = conn.execute(text("""
                SELECT COUNT(*) FROM dbo.ManufacturerInventory
                WHERE BrandId = :brand_id AND RegionCode = 'EU'
                  AND (AvailabilitySource <> 'manufacturer_direct'
                       OR AvailabilitySource IS NULL
                       OR (PriceAmount IS NOT NULL AND PriceCurrency <> 'EUR'))
            """), {"brand_id": brand_id}).scalar_one()
            if invalid:
                raise RuntimeError(f"EU MFA validation failed for {brand}")
            protected_after = region_counts(conn)
            if protected_after.get("AU") != protected_before.get("AU"):
                raise RuntimeError(f"AU ManufacturerInventory changed while importing {brand}")
            if protected_after.get("ID") != protected_before.get("ID"):
                raise RuntimeError(f"ID ManufacturerInventory changed while importing {brand}")
            if protected_after.get("<NULL>", 0) != protected_before.get("<NULL>", 0):
                raise RuntimeError(f"NULL RegionCode rows changed while importing {brand}")
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise
    elapsed = time.perf_counter() - started
    return {
        "brand": brand,
        "rowsLoaded": len(rows),
        "rowsDeleted": max(deleted, 0),
        "rowsInserted": inserted,
        "elapsedSeconds": round(elapsed, 3),
        "rowsPerSecond": round(inserted / elapsed, 2) if elapsed else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--brands", default="")
    args = parser.parse_args()
    allowed = {item.strip() for item in args.brands.split(",") if item.strip()}
    rows = [row for row in load_rows() if not allowed or row["brandName"] in allowed]
    engine = build_engine()  # retains the existing 60-second connection acquisition timeout

    with connect_with_retry(engine) as conn:
        before = region_counts(conn)
        prepared = prepare_rows(conn, rows)

    grouped = defaultdict(list)
    for item in prepared:
        grouped[item[0]["brandName"]].append(item)
    diagnostics = []
    total_started = time.perf_counter()
    if args.apply:
        for brand in sorted(grouped):
            result = import_brand(engine, brand, grouped[brand])
            diagnostics.append(result)
            print(json.dumps(result), flush=True)
    else:
        for brand in sorted(grouped):
            items = grouped[brand]
            diagnostics.append({
                "brand": brand,
                "rowsLoaded": len(items),
                "modelLinked": sum(item[2] is not None for item in items),
                "sizeLinked": sum(item[3] is not None for item in items),
            })

    with connect_with_retry(engine) as conn:
        after = region_counts(conn)
    if after.get("AU") != before.get("AU") or after.get("ID") != before.get("ID"):
        raise RuntimeError("Protected AU or ID ManufacturerInventory count changed")
    if after.get("<NULL>", 0) != before.get("<NULL>", 0):
        raise RuntimeError("NULL RegionCode ManufacturerInventory count changed")
    result = {
        "mode": "apply" if args.apply else "dry_run",
        "chunkSize": CHUNK_SIZE,
        "before": before,
        "after": after,
        "brands": diagnostics,
        "totalElapsedSeconds": round(time.perf_counter() - total_started, 3),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
