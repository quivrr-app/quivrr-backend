from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
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
LINK_AUDIT_FILE = Path("scripts/manufacturer_availability/output/eu_mfa_link_audit.json")
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
                "width": row.get("width"),
                "thickness": row.get("thickness"),
                "volumeLitres": row.get("volumeLitres"),
                "construction": row.get("construction"),
            },
            model_id,
            sizes,
        ) if model_id else None
        prepared.append((row, brand_id, model_id, size["boardSizeId"] if size else None))
    return prepared


def source_key(row):
    brand = clean(row.get("brandName"))
    product_id = clean(row.get("sourceProductId"))
    variant_id = clean(row.get("sourceStockVariantId") or row.get("sourceVariantId"))
    if product_id and variant_id:
        return brand, product_id, variant_id
    return brand, clean(row.get("productUrl")), clean(row.get("lengthFeetInches"))


def load_current_rows(conn, brands):
    rows = conn.execute(text("""
        SELECT ManufacturerInventoryId, BrandName, BoardModelId, BoardSizeId,
               RawProductTitle, ProductUrl, LengthFeetInches, Width, Thickness,
               VolumeLitres, Construction, SourcePayload
        FROM dbo.ManufacturerInventory
        WHERE RegionCode = 'EU'
          AND AvailabilitySource = 'manufacturer_direct'
    """)).fetchall()
    current = {}
    for row in rows:
        if row.BrandName not in brands:
            continue
        payload = json.loads(row.SourcePayload) if row.SourcePayload else {}
        key = source_key(payload or {
            "brandName": row.BrandName,
            "productUrl": row.ProductUrl,
            "lengthFeetInches": row.LengthFeetInches,
        })
        current[key] = row
    return current


def build_link_audit(prepared, current):
    brand_stats = defaultdict(lambda: {
        "beforeModelLinks": 0, "afterModelLinks": 0,
        "beforeSizeLinks": 0, "afterSizeLinks": 0,
        "additionalModelLinks": 0, "additionalSizeLinks": 0,
    })
    blockers = defaultdict(Counter)
    model_updates = []
    size_updates = []
    newly_linked = []
    still_unlinked = []

    for row, _brand_id, model_id, size_id in prepared:
        brand = row["brandName"]
        live = current.get(source_key(row))
        if live is None:
            blockers[brand]["source_row_not_found"] += 1
            continue
        stats = brand_stats[brand]
        before_model = live.BoardModelId is not None
        before_size = live.BoardSizeId is not None
        after_model = before_model or model_id is not None
        after_size = before_size or size_id is not None
        stats["beforeModelLinks"] += before_model
        stats["afterModelLinks"] += after_model
        stats["beforeSizeLinks"] += before_size
        stats["afterSizeLinks"] += after_size
        if not before_model and model_id is not None:
            stats["additionalModelLinks"] += 1
            model_updates.append({
                "inventory_id": int(live.ManufacturerInventoryId),
                "board_model_id": model_id,
            })
        if not before_size and size_id is not None:
            stats["additionalSizeLinks"] += 1
            size_updates.append({
                "inventory_id": int(live.ManufacturerInventoryId),
                "board_size_id": size_id,
            })
            newly_linked.append({
                "brand": brand,
                "rawTitle": row.get("rawProductTitle"),
                "model": row.get("modelName"),
                "length": row.get("lengthFeetInches"),
                "width": row.get("width"),
                "thickness": row.get("thickness"),
                "volume": row.get("volumeLitres"),
                "construction": row.get("construction"),
                "boardSizeId": size_id,
                "productUrl": row.get("productUrl"),
            })
        if not after_size:
            reason = (
                "model_not_linked" if not after_model else
                "missing_length" if not row.get("lengthFeetInches") else
                "ambiguous_or_no_canonical_size"
            )
            blockers[brand][reason] += 1
            still_unlinked.append({
                "brand": brand,
                "rawTitle": row.get("rawProductTitle"),
                "model": row.get("modelName"),
                "length": row.get("lengthFeetInches"),
                "width": row.get("width"),
                "thickness": row.get("thickness"),
                "volume": row.get("volumeLitres"),
                "construction": row.get("construction"),
                "reason": reason,
                "productUrl": row.get("productUrl"),
            })

    return {
        "regionCode": REGION,
        "brands": [
            {"brand": brand, **stats, "topRemainingBlockers": dict(blockers[brand].most_common())}
            for brand, stats in sorted(brand_stats.items())
        ],
        "newlyLinkedSample": newly_linked[:30],
        "stillUnlinkedSample": still_unlinked[:30],
        "modelUpdates": model_updates,
        "sizeUpdates": size_updates,
    }


def apply_links(engine, audit):
    with connect_with_retry(engine) as conn:
        transaction = conn.begin()
        try:
            before = region_counts(conn)
            if audit["modelUpdates"]:
                conn.execute(text("""
                    UPDATE dbo.ManufacturerInventory
                    SET BoardModelId = :board_model_id
                    WHERE ManufacturerInventoryId = :inventory_id
                      AND RegionCode = 'EU'
                      AND BoardModelId IS NULL
                """), audit["modelUpdates"])
            if audit["sizeUpdates"]:
                conn.execute(text("""
                    UPDATE dbo.ManufacturerInventory
                    SET BoardSizeId = :board_size_id
                    WHERE ManufacturerInventoryId = :inventory_id
                      AND RegionCode = 'EU'
                      AND BoardModelId IS NOT NULL
                      AND BoardSizeId IS NULL
                """), audit["sizeUpdates"])
            after = region_counts(conn)
            if after.get("AU") != before.get("AU") or after.get("ID") != before.get("ID"):
                raise RuntimeError("Protected AU or ID ManufacturerInventory count changed")
            if after.get("EU") != before.get("EU") or after.get("<NULL>", 0) != before.get("<NULL>", 0):
                raise RuntimeError("EU count or NULL RegionCode count changed")
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise
    return before, after


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
    parser.add_argument("--apply-links", action="store_true")
    parser.add_argument("--brands", default="")
    args = parser.parse_args()
    allowed = {item.strip() for item in args.brands.split(",") if item.strip()}
    rows = [row for row in load_rows() if not allowed or row["brandName"] in allowed]
    engine = build_engine()  # retains the existing 60-second connection acquisition timeout

    with connect_with_retry(engine) as conn:
        before = region_counts(conn)
        prepared = prepare_rows(conn, rows)
        current = load_current_rows(conn, {row[0]["brandName"] for row in prepared})

    link_audit = build_link_audit(prepared, current)
    public_link_audit = {
        key: value for key, value in link_audit.items()
        if key not in {"modelUpdates", "sizeUpdates"}
    }
    LINK_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    LINK_AUDIT_FILE.write_text(json.dumps(public_link_audit, indent=2), encoding="utf-8")

    grouped = defaultdict(list)
    for item in prepared:
        grouped[item[0]["brandName"]].append(item)
    diagnostics = []
    total_started = time.perf_counter()
    if args.apply_links:
        link_before, link_after = apply_links(engine, link_audit)
        diagnostics = public_link_audit["brands"]
    elif args.apply:
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
        "mode": "apply_links" if args.apply_links else "apply" if args.apply else "dry_run",
        "chunkSize": CHUNK_SIZE,
        "before": before,
        "after": after,
        "brands": diagnostics,
        "linkAudit": public_link_audit,
        "totalElapsedSeconds": round(time.perf_counter() - total_started, 3),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
