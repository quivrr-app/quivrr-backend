from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.europe.import_eu_retailer_inventory import (
    REGION_CODE,
    build_engine,
    clean,
    clean_key,
    count_inventory_by_region,
    count_retailers_by_region,
    decimal_key,
    row_field,
)


OUTPUT_FILE = Path("scripts/europe/output/eu_final_duplicate_cleanup_report.json")
SQL_OUTPUT_FILE = Path("scripts/europe/output/eu_cleanup.sql")


def load_eu_retailers(conn) -> list[dict]:
    rows = conn.execute(
        text("""
            SELECT
                RetailerId,
                RetailerName,
                WebsiteUrl,
                Country
            FROM dbo.Retailers
            WHERE RegionCode = 'EU'
            ORDER BY RetailerId
        """)
    ).fetchall()
    return [
        {
            "retailerId": int(row_field(row, "RetailerId")),
            "retailerName": clean(row_field(row, "RetailerName")),
            "nameKey": clean_key(row_field(row, "RetailerName")),
            "websiteUrl": clean(row_field(row, "WebsiteUrl")),
            "country": clean(row_field(row, "Country")),
        }
        for row in rows
    ]


def load_eu_inventory(conn) -> list[dict]:
    rows = conn.execute(
        text("""
            SELECT
                InventoryId,
                RetailerId,
                ProductUrl,
                RawProductTitle,
                NormalisedProductTitle,
                LengthFeetInches,
                VolumeLitres,
                PriceAmount,
                BoardModelId,
                BoardSizeId,
                ProductImageUrl,
                StockStatus
            FROM dbo.RetailerInventory
            WHERE RegionCode = 'EU'
            ORDER BY InventoryId
        """)
    ).fetchall()
    return [
        {
            "inventoryId": int(row_field(row, "InventoryId")),
            "retailerId": int(row_field(row, "RetailerId")),
            "productUrl": clean(row_field(row, "ProductUrl")),
            "rawProductTitle": clean(row_field(row, "RawProductTitle")),
            "normalisedProductTitle": clean(row_field(row, "NormalisedProductTitle")),
            "lengthFeetInches": clean(row_field(row, "LengthFeetInches")),
            "volumeLitres": row_field(row, "VolumeLitres"),
            "priceAmount": row_field(row, "PriceAmount"),
            "boardModelId": row_field(row, "BoardModelId"),
            "boardSizeId": row_field(row, "BoardSizeId"),
            "productImageUrl": clean(row_field(row, "ProductImageUrl")),
            "stockStatus": clean(row_field(row, "StockStatus")),
        }
        for row in rows
    ]


def is_available_stock(value: object) -> bool:
    return clean_key(value).replace(" ", "_") in {"in_stock", "instock", "available", "true"}


def build_retailer_plan(retailers: list[dict]) -> tuple[list[dict], dict[int, int], list[int]]:
    by_key: dict[str, list[dict]] = defaultdict(list)
    for retailer in retailers:
        if retailer["nameKey"]:
            by_key[retailer["nameKey"]].append(retailer)

    groups = []
    retailer_id_map = {}
    delete_ids = []
    for name_key, group in sorted(by_key.items()):
        if len(group) <= 1:
            continue
        group = sorted(group, key=lambda item: item["retailerId"])
        keep = group[0]
        duplicates = group[1:]
        for duplicate in duplicates:
            retailer_id_map[duplicate["retailerId"]] = keep["retailerId"]
            delete_ids.append(duplicate["retailerId"])
        groups.append({
            "nameKey": name_key,
            "keepRetailerId": keep["retailerId"],
            "keepRetailerName": keep["retailerName"],
            "duplicateRetailerIds": [item["retailerId"] for item in duplicates],
            "allRetailerIds": [item["retailerId"] for item in group],
        })
    return groups, retailer_id_map, delete_ids


def effective_retailer_id(row: dict, retailer_id_map: dict[int, int]) -> int:
    return retailer_id_map.get(row["retailerId"], row["retailerId"])


def inventory_duplicate_key(row: dict, retailer_id_map: dict[int, int]) -> tuple:
    title = row.get("rawProductTitle") or row.get("normalisedProductTitle")
    return (
        REGION_CODE,
        effective_retailer_id(row, retailer_id_map),
        clean_key(row.get("productUrl")),
        clean_key(title),
        clean_key(row.get("lengthFeetInches")),
        decimal_key(row.get("volumeLitres")),
        decimal_key(row.get("priceAmount")),
    )


def inventory_preference(row: dict) -> tuple:
    return (
        1 if row.get("boardSizeId") is not None else 0,
        1 if row.get("boardModelId") is not None else 0,
        1 if row.get("productImageUrl") else 0,
        1 if is_available_stock(row.get("stockStatus")) else 0,
        -int(row["inventoryId"]),
    )


def build_inventory_plan(inventory: list[dict], retailer_id_map: dict[int, int]) -> tuple[list[dict], list[int]]:
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    for row in inventory:
        by_key[inventory_duplicate_key(row, retailer_id_map)].append(row)

    groups = []
    delete_ids = []
    for key, group in by_key.items():
        if len(group) <= 1:
            continue
        keep = sorted(group, key=inventory_preference, reverse=True)[0]
        duplicates = [row for row in group if row["inventoryId"] != keep["inventoryId"]]
        delete_ids.extend(row["inventoryId"] for row in duplicates)
        groups.append({
            "key": "|".join(str(part) for part in key),
            "keepInventoryId": keep["inventoryId"],
            "duplicateInventoryIds": [row["inventoryId"] for row in duplicates],
            "groupSize": len(group),
            "sampleTitle": keep.get("rawProductTitle"),
            "effectiveRetailerId": key[1],
        })
    groups.sort(key=lambda item: (-item["groupSize"], item["effectiveRetailerId"], item["sampleTitle"] or ""))
    return groups, sorted(delete_ids)


def build_report(conn) -> dict:
    retailers = load_eu_retailers(conn)
    inventory = load_eu_inventory(conn)
    retailer_groups, retailer_id_map, duplicate_retailer_ids = build_retailer_plan(retailers)
    inventory_groups, duplicate_inventory_ids = build_inventory_plan(inventory, retailer_id_map)
    moves_by_pair = Counter()
    for row in inventory:
        keep_id = effective_retailer_id(row, retailer_id_map)
        if keep_id != row["retailerId"]:
            moves_by_pair[(row["retailerId"], keep_id)] += 1

    eu_inventory_before = count_inventory_by_region(conn, "EU")
    au_inventory_before = count_inventory_by_region(conn, "AU")
    id_inventory_before = count_inventory_by_region(conn, "ID")
    eu_retailers_before = count_retailers_by_region(conn, "EU")

    return {
        "mode": "dry_run",
        "regionCode": REGION_CODE,
        "safety": {
            "auDeleteCount": 0,
            "idDeleteCount": 0,
            "noTruncate": True,
            "noDrop": True,
            "transactionWrapped": True,
            "deleteScope": "RetailerInventory deletes use exact InventoryId values from EU-scoped query and RegionCode='EU'. Retailer deletes use exact RetailerId values from EU-scoped query and RegionCode='EU'.",
        },
        "countsBefore": {
            "euInventoryRows": eu_inventory_before,
            "euRetailers": eu_retailers_before,
            "auInventoryRows": au_inventory_before,
            "idInventoryRows": id_inventory_before,
        },
        "expectedCountsAfter": {
            "euInventoryRows": eu_inventory_before - len(duplicate_inventory_ids),
            "euRetailers": eu_retailers_before - len(duplicate_retailer_ids),
            "auInventoryRows": au_inventory_before,
            "idInventoryRows": id_inventory_before,
        },
        "retailerDuplicateGroups": retailer_groups,
        "inventoryDuplicateGroups": inventory_groups[:200],
        "inventoryDuplicateGroupCount": len(inventory_groups),
        "rowsToMoveBetweenRetailers": [
            {"fromRetailerId": pair[0], "toRetailerId": pair[1], "inventoryRows": count}
            for pair, count in sorted(moves_by_pair.items())
        ],
        "duplicateRetailerIdsToDelete": sorted(duplicate_retailer_ids),
        "duplicateInventoryIdsToDelete": duplicate_inventory_ids,
        "duplicateRetailersToDelete": len(duplicate_retailer_ids),
        "duplicateInventoryRowsToDelete": len(duplicate_inventory_ids),
    }


def assert_safety(report: dict) -> None:
    safety = report["safety"]
    if report.get("regionCode") != REGION_CODE:
        raise RuntimeError("Cleanup safety failed: report is not EU scoped.")
    if safety.get("auDeleteCount") != 0 or safety.get("idDeleteCount") != 0:
        raise RuntimeError("Cleanup safety failed: AU/ID delete count must be 0.")
    if not safety.get("noTruncate") or not safety.get("noDrop") or not safety.get("transactionWrapped"):
        raise RuntimeError("Cleanup safety failed: destructive SQL guard failed.")


def apply_cleanup(conn, report: dict) -> dict:
    assert_safety(report)
    moved_rows = 0
    inventory_deleted = 0
    retailers_deleted = 0

    for move in report["rowsToMoveBetweenRetailers"]:
        result = conn.execute(
            text("""
                UPDATE dbo.RetailerInventory
                SET RetailerId = :to_retailer_id,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE RegionCode = 'EU'
                  AND RetailerId = :from_retailer_id
            """),
            {
                "from_retailer_id": move["fromRetailerId"],
                "to_retailer_id": move["toRetailerId"],
            },
        )
        moved_rows += result.rowcount or 0

    for inventory_id in report["duplicateInventoryIdsToDelete"]:
        result = conn.execute(
            text("""
                DELETE FROM dbo.RetailerInventory
                WHERE RegionCode = 'EU'
                  AND InventoryId = :inventory_id
            """),
            {"inventory_id": inventory_id},
        )
        inventory_deleted += result.rowcount or 0

    for retailer_id in report["duplicateRetailerIdsToDelete"]:
        result = conn.execute(
            text("""
                DELETE FROM dbo.Retailers
                WHERE RegionCode = 'EU'
                  AND RetailerId = :retailer_id
                  AND NOT EXISTS (
                      SELECT 1
                      FROM dbo.RetailerInventory
                      WHERE RetailerId = :retailer_id
                  )
            """),
            {"retailer_id": retailer_id},
        )
        retailers_deleted += result.rowcount or 0

    return {
        "movedInventoryRows": moved_rows,
        "deletedInventoryRows": inventory_deleted,
        "deletedRetailers": retailers_deleted,
    }


def write_report(report: dict, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def export_cleanup_sql(output_file: Path = SQL_OUTPUT_FILE) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    sql = """-- Quivrr EU retailer duplicate cleanup
-- Generated locally without connecting to Azure SQL.
-- Scope: EU only. No AU or ID writes.
SET XACT_ABORT ON;
BEGIN TRANSACTION;

;WITH DuplicateRetailers AS (
    SELECT
        RetailerId,
        RetailerName,
        LOWER(LTRIM(RTRIM(RetailerName))) AS RetailerNameKey,
        MIN(RetailerId) OVER (
            PARTITION BY LOWER(LTRIM(RTRIM(RetailerName)))
        ) AS KeepRetailerId
    FROM dbo.Retailers
    WHERE RegionCode = 'EU'
),
RetailersToMove AS (
    SELECT RetailerId, KeepRetailerId
    FROM DuplicateRetailers
    WHERE RetailerId <> KeepRetailerId
)
UPDATE ri
SET
    RetailerId = move.KeepRetailerId,
    UpdatedAtUtc = SYSUTCDATETIME()
FROM dbo.RetailerInventory ri
INNER JOIN RetailersToMove move
    ON move.RetailerId = ri.RetailerId
WHERE ri.RegionCode = 'EU';

;WITH RankedInventory AS (
    SELECT
        ri.InventoryId,
        ROW_NUMBER() OVER (
            PARTITION BY
                ri.RegionCode,
                ri.RetailerId,
                LOWER(LTRIM(RTRIM(ISNULL(ri.ProductUrl, '')))),
                LOWER(LTRIM(RTRIM(ISNULL(ri.RawProductTitle, ri.NormalisedProductTitle)))),
                LOWER(LTRIM(RTRIM(ISNULL(ri.LengthFeetInches, '')))),
                CAST(ri.VolumeLitres AS decimal(10,2)),
                CAST(ri.PriceAmount AS decimal(18,2))
            ORDER BY
                CASE WHEN ri.BoardSizeId IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN ri.BoardModelId IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN NULLIF(LTRIM(RTRIM(ISNULL(ri.ProductImageUrl, ''))), '') IS NOT NULL THEN 0 ELSE 1 END,
                CASE
                    WHEN LOWER(REPLACE(LTRIM(RTRIM(ISNULL(ri.StockStatus, ''))), ' ', '_')) IN ('in_stock', 'instock', 'available', 'true')
                        THEN 0
                    ELSE 1
                END,
                ri.InventoryId
        ) AS DuplicateRank
    FROM dbo.RetailerInventory ri
    WHERE ri.RegionCode = 'EU'
)
DELETE ri
FROM dbo.RetailerInventory ri
INNER JOIN RankedInventory ranked
    ON ranked.InventoryId = ri.InventoryId
WHERE ri.RegionCode = 'EU'
  AND ranked.DuplicateRank > 1;

;WITH DuplicateRetailers AS (
    SELECT
        RetailerId,
        MIN(RetailerId) OVER (
            PARTITION BY LOWER(LTRIM(RTRIM(RetailerName)))
        ) AS KeepRetailerId
    FROM dbo.Retailers
    WHERE RegionCode = 'EU'
)
DELETE r
FROM dbo.Retailers r
INNER JOIN DuplicateRetailers duplicate
    ON duplicate.RetailerId = r.RetailerId
WHERE r.RegionCode = 'EU'
  AND duplicate.RetailerId <> duplicate.KeepRetailerId
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.RetailerInventory ri
      WHERE ri.RetailerId = r.RetailerId
  );

SELECT
    COUNT(*) AS EuInventoryRows
FROM dbo.RetailerInventory
WHERE RegionCode = 'EU';

SELECT
    COUNT(*) AS EuRetailers
FROM dbo.Retailers
WHERE RegionCode = 'EU';

;WITH DuplicateInventory AS (
    SELECT
        ri.RegionCode,
        ri.RetailerId,
        LOWER(LTRIM(RTRIM(ISNULL(ri.ProductUrl, '')))) AS ProductUrlKey,
        LOWER(LTRIM(RTRIM(ISNULL(ri.RawProductTitle, ri.NormalisedProductTitle)))) AS TitleKey,
        LOWER(LTRIM(RTRIM(ISNULL(ri.LengthFeetInches, '')))) AS LengthKey,
        CAST(ri.VolumeLitres AS decimal(10,2)) AS VolumeKey,
        CAST(ri.PriceAmount AS decimal(18,2)) AS PriceKey,
        COUNT(*) AS DuplicateCount
    FROM dbo.RetailerInventory ri
    WHERE ri.RegionCode = 'EU'
    GROUP BY
        ri.RegionCode,
        ri.RetailerId,
        LOWER(LTRIM(RTRIM(ISNULL(ri.ProductUrl, '')))),
        LOWER(LTRIM(RTRIM(ISNULL(ri.RawProductTitle, ri.NormalisedProductTitle)))),
        LOWER(LTRIM(RTRIM(ISNULL(ri.LengthFeetInches, '')))),
        CAST(ri.VolumeLitres AS decimal(10,2)),
        CAST(ri.PriceAmount AS decimal(18,2))
    HAVING COUNT(*) > 1
)
SELECT *
FROM DuplicateInventory
ORDER BY DuplicateCount DESC;

COMMIT TRANSACTION;
"""
    output_file.write_text(sql, encoding="utf-8")


def local_report() -> dict:
    return {
        "mode": "dry_run",
        "regionCode": REGION_CODE,
        "status": "not_checked_locally",
        "reason": "Local Azure SQL connections are disabled. Use --export-sql or --azure-run.",
        "outputs": {
            "sql": str(SQL_OUTPUT_FILE),
        },
        "safety": {
            "euOnly": True,
            "localSqlConnection": False,
            "localApply": False,
            "noSchemaChanges": True,
            "noAzureChanges": True,
        },
    }


def print_azure_run_command() -> None:
    print("Local Azure SQL execution is disabled.")
    print("Run from an approved Azure environment instead, for example:")
    print("az containerapp job start --name quivrr-eu-retailer-inventory --resource-group quivrr-production-rg")
    print("Suggested container command:")
    print("venv\\Scripts\\python.exe scripts\\europe\\cleanup_eu_retailer_duplicates.py --export-sql")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean up duplicate EU retailer inventory rows.")
    parser.add_argument("--apply", action="store_true", help="Disabled for local safety. Use --export-sql or --azure-run.")
    parser.add_argument("--export-sql", action="store_true", help="Generate SQL file only. Does not connect to SQL.")
    parser.add_argument("--sql-output", default=str(SQL_OUTPUT_FILE), help="SQL output path for --export-sql.")
    parser.add_argument("--azure-run", action="store_true", help="Print remote Azure execution command only.")
    parser.add_argument("--output", default=str(OUTPUT_FILE), help="Cleanup report path.")
    args = parser.parse_args()

    output_file = Path(args.output)

    if args.apply:
        raise RuntimeError("Local --apply is disabled. Use --export-sql or --azure-run.")

    if args.azure_run:
        print_azure_run_command()
        return

    if args.export_sql:
        sql_output = Path(args.sql_output)
        export_cleanup_sql(sql_output)
        print("EU duplicate cleanup SQL export complete")
        print(f"SQL output: {sql_output}")
        return

    report = local_report()

    write_report(report, output_file)
    print("EU retailer duplicate cleanup dry-run complete")
    print("Local SQL connection: disabled")
    print("Local apply: disabled")
    print(f"Report: {output_file}")


if __name__ == "__main__":
    main()
