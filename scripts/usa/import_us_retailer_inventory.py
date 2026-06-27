from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.europe import import_eu_retailer_inventory as eu_import  # noqa: E402
from scripts.usa.us_link_projection_rules import (  # noqa: E402
    excluded_product_type,
    normalise_brand_and_model_for_projection,
)
from utils.structured_logging import emit_event, update_job_state  # noqa: E402


REGION_CODE = "US"
PRICE_CURRENCY = "USD"
INPUT_FILE = Path("scrapers/retailers/usa/output/us_normalised_inventory.json")
OUTPUT_FILE = Path("scripts/usa/output/us_retailer_import_dry_run_report.json")
APPLY_OUTPUT_FILE = Path("scripts/usa/output/us_retailer_import_apply_report.json")
LINK_REPORT_FILE = Path("scripts/usa/output/us_retailer_canonical_link_report.json")
LINK_APPLY_REPORT_FILE = Path("scripts/usa/output/us_canonical_link_apply_report.json")
ROLLBACK_PLAN_FILE = Path("scripts/usa/output/us_retailer_import_rollback_plan.json")
ROLLBACK_SQL_FILE = Path("scripts/usa/output/us_retailer_import_rollback.sql")
SQL_OUTPUT_FILE = Path("scripts/usa/output/us_import.sql")
PRIORITY_RETAILERS = [
    "Surf Station",
    "Jack's Surfboards",
    "Real Watersports",
    "Cleanline Surf",
    "Hawaiian South Shore",
    "Bird's Surf Shed",
    "Island Water Sports",
    "Surf N Sea",
    "Kimo's Surf Hut",
    "Moment Surf Co",
    "Degree 33 Surfboards",
    "Surfboard Broker",
    "Infinity Surfboards",
    "Walden Surfboards",
    "Stewart Surfboards",
    "Bing Surfboards",
    "Robert August Surf Company",
    "Dark Arts Surf",
    "Catalyst Surf Shop",
    "Warm Winds",
]
CONFIRM_TOKEN = "APPLY_US"
SCHEMA_DECIMAL_QUANTUM = {
    "price_amount": Decimal("0.01"),
    "volume": Decimal("0.01"),
    "confidence": Decimal("0.01"),
    "estimated_shipping_aud": Decimal("0.01"),
}


def _sql_region(sql: str) -> str:
    return sql.replace("'EU'", "'US'").replace("'EUR'", "'USD'")


def configure_eu_base() -> None:
    eu_import.INPUT_FILE = INPUT_FILE
    eu_import.OUTPUT_FILE = OUTPUT_FILE
    eu_import.APPLY_OUTPUT_FILE = APPLY_OUTPUT_FILE
    eu_import.LINK_REPORT_FILE = LINK_REPORT_FILE
    eu_import.LINK_APPLY_REPORT_FILE = LINK_APPLY_REPORT_FILE
    eu_import.SQL_OUTPUT_FILE = SQL_OUTPUT_FILE
    eu_import.REGION_CODE = REGION_CODE
    eu_import.PRICE_CURRENCY = PRICE_CURRENCY


def quantize_for_sql(value: object, quantum: Decimal) -> float | None:
    number = eu_import.decimal_or_none(value)
    if number is None:
        return None
    return float(number.quantize(quantum, rounding=ROUND_HALF_UP))


def conform_inventory_payload_for_sql(payload: dict) -> dict:
    # Preserve raw scrape output and only conform DB-bound numeric precision to
    # the live RetailerInventory schema so pyodbc batch updates do not fail on
    # mixed decimal scales.
    conformed = dict(payload)
    conformed["price_amount"] = quantize_for_sql(
        payload.get("price_amount"), SCHEMA_DECIMAL_QUANTUM["price_amount"]
    )
    conformed["volume"] = quantize_for_sql(
        payload.get("volume"), SCHEMA_DECIMAL_QUANTUM["volume"]
    )
    conformed["confidence"] = quantize_for_sql(
        payload.get("confidence"), SCHEMA_DECIMAL_QUANTUM["confidence"]
    )
    if "estimated_shipping_aud" in conformed:
        conformed["estimated_shipping_aud"] = quantize_for_sql(
            payload.get("estimated_shipping_aud"),
            SCHEMA_DECIMAL_QUANTUM["estimated_shipping_aud"],
        )
    return conformed


def to_json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [to_json_safe(item) for item in value]
    return value


def load_us_inventory_rows(conn) -> list[dict]:
    rows = conn.execute(
        text(
            _sql_region(
                """
                SELECT
                    ri.InventoryId,
                    ri.RetailerId,
                    r.RetailerName,
                    ri.BrandId,
                    b.BrandName,
                    ri.BoardModelId,
                    ri.BoardSizeId,
                    ri.RawProductTitle,
                    ri.NormalisedProductTitle,
                    ri.LengthFeetInches,
                    ri.Width,
                    ri.Thickness,
                    ri.VolumeLitres,
                    ri.Construction,
                    ri.PriceCurrency,
                    ri.RegionCode
                FROM dbo.RetailerInventory ri
                INNER JOIN dbo.Retailers r
                    ON r.RetailerId = ri.RetailerId
                LEFT JOIN dbo.Brands b
                    ON b.BrandId = ri.BrandId
                WHERE ri.RegionCode = 'EU'
                  AND ri.IsActive = 1
                """
            )
        )
    ).fetchall()
    inventory = []
    for row in rows:
        inventory.append(
            {
                "inventoryId": int(eu_import.row_field(row, "InventoryId")),
                "retailerId": int(eu_import.row_field(row, "RetailerId")),
                "retailerName": eu_import.clean(eu_import.row_field(row, "RetailerName")),
                "brandId": int(eu_import.row_field(row, "BrandId"))
                if eu_import.row_field(row, "BrandId") is not None
                else None,
                "brandName": eu_import.clean(eu_import.row_field(row, "BrandName")),
                "boardModelId": int(eu_import.row_field(row, "BoardModelId"))
                if eu_import.row_field(row, "BoardModelId") is not None
                else None,
                "boardSizeId": int(eu_import.row_field(row, "BoardSizeId"))
                if eu_import.row_field(row, "BoardSizeId") is not None
                else None,
                "rawProductTitle": eu_import.clean(
                    eu_import.row_field(row, "RawProductTitle")
                ),
                "normalisedProductTitle": eu_import.clean(
                    eu_import.row_field(row, "NormalisedProductTitle")
                ),
                "lengthFeetInches": eu_import.clean(
                    eu_import.row_field(row, "LengthFeetInches")
                ),
                "width": eu_import.clean(eu_import.row_field(row, "Width")),
                "thickness": eu_import.clean(eu_import.row_field(row, "Thickness")),
                "volumeLitres": eu_import.decimal_or_none(
                    eu_import.row_field(row, "VolumeLitres")
                ),
                "construction": eu_import.clean(
                    eu_import.row_field(row, "Construction")
                ),
                "priceCurrency": eu_import.clean(
                    eu_import.row_field(row, "PriceCurrency")
                ),
                "regionCode": eu_import.clean(eu_import.row_field(row, "RegionCode")),
            }
        )
    return inventory


def priority_retailer_counts(conn) -> list[dict]:
    quoted = ", ".join("'" + name.replace("'", "''") + "'" for name in PRIORITY_RETAILERS)
    rows = conn.execute(
        text(
            _sql_region(
                f"""
                SELECT
                    r.RegionCode,
                    r.RetailerName,
                    COUNT(ri.InventoryId) AS InventoryRows,
                    SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModels,
                    SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizes
                FROM dbo.Retailers r
                LEFT JOIN dbo.RetailerInventory ri
                  ON ri.RetailerId = r.RetailerId
                 AND ri.RegionCode = r.RegionCode
                WHERE r.RetailerName IN ({quoted})
                GROUP BY r.RegionCode, r.RetailerName
                ORDER BY r.RegionCode, r.RetailerName
                """
            )
        )
    ).fetchall()
    return [
        {
            "regionCode": eu_import.clean(eu_import.row_field(row, "RegionCode")),
            "retailerName": eu_import.clean(eu_import.row_field(row, "RetailerName")),
            "inventoryRows": int(eu_import.row_field(row, "InventoryRows") or 0),
            "linkedBoardModelIdRows": int(eu_import.row_field(row, "LinkedModels") or 0),
            "linkedBoardSizeIdRows": int(eu_import.row_field(row, "LinkedSizes") or 0),
        }
        for row in rows
    ]


def sample_us_rows(conn) -> list[dict]:
    rows = conn.execute(
        text(
            _sql_region(
                """
                SELECT TOP 10
                    r.RetailerName,
                    ri.RawProductTitle,
                    ri.PriceAmount,
                    ri.PriceCurrency,
                    ri.RegionCode
                FROM dbo.RetailerInventory ri
                JOIN dbo.Retailers r
                    ON r.RetailerId = ri.RetailerId
                WHERE ri.RegionCode = 'EU'
                ORDER BY ri.UpdatedAtUtc DESC, ri.InventoryId DESC
                """
            )
        )
    ).fetchall()
    return [
        {
            "retailerName": row.RetailerName,
            "rawProductTitle": row.RawProductTitle,
            "priceAmount": float(row.PriceAmount) if row.PriceAmount is not None else None,
            "priceCurrency": row.PriceCurrency,
            "regionCode": row.RegionCode,
        }
        for row in rows
    ]


def get_or_create_retailer(conn, retailer: dict) -> tuple[int, bool]:
    existing = conn.execute(
        text(
            _sql_region(
                """
                SELECT TOP 1 RetailerId
                FROM dbo.Retailers
                WHERE RetailerName = :retailer_name
                  AND RegionCode = 'EU'
                ORDER BY RetailerId
                """
            )
        ),
        retailer,
    ).fetchone()
    if existing:
        conn.execute(
            text(
                _sql_region(
                    """
                    UPDATE dbo.Retailers
                    SET WebsiteUrl = :website_url,
                        Country = :country,
                        IsActive = 1,
                        UpdatedAtUtc = SYSUTCDATETIME()
                    WHERE RetailerId = :retailer_id
                      AND RegionCode = 'EU'
                    """
                )
            ),
            {**retailer, "retailer_id": existing.RetailerId},
        )
        return int(existing.RetailerId), False

    row = conn.execute(
        text(
            _sql_region(
                """
                INSERT INTO dbo.Retailers (
                    RetailerName,
                    WebsiteUrl,
                    Country,
                    RegionCode,
                    IsActive,
                    CreatedAtUtc,
                    UpdatedAtUtc
                )
                OUTPUT INSERTED.RetailerId
                VALUES (
                    :retailer_name,
                    :website_url,
                    :country,
                    'EU',
                    1,
                    SYSUTCDATETIME(),
                    SYSUTCDATETIME()
                )
                """
            )
        ),
        retailer,
    ).fetchone()
    return int(row.RetailerId), True


def existing_inventory_id(conn, row: dict) -> int | None:
    existing = conn.execute(
        text(
            _sql_region(
                """
                SELECT TOP 1 InventoryId
                FROM dbo.RetailerInventory
                WHERE RetailerId = :retailer_id
                  AND RegionCode = 'EU'
                  AND ISNULL(ProductUrl, '') = ISNULL(:product_url, '')
                  AND ISNULL(RawProductTitle, '') = ISNULL(:raw_title, '')
                  AND ISNULL(LengthFeetInches, '') = ISNULL(:length, '')
                  AND (
                        (VolumeLitres IS NULL AND :volume IS NULL)
                        OR VolumeLitres = :volume
                        OR (VolumeLitres IS NULL AND :volume IS NOT NULL)
                      )
                ORDER BY InventoryId
                """
            )
        ),
        row,
    ).fetchone()
    return int(eu_import.row_field(existing, "InventoryId")) if existing else None


def load_existing_us_inventory(conn) -> dict[tuple, int]:
    rows = conn.execute(
        text(
            _sql_region(
                """
                SELECT
                    InventoryId,
                    RetailerId,
                    ProductUrl,
                    RawProductTitle,
                    LengthFeetInches,
                    VolumeLitres
                FROM dbo.RetailerInventory
                WHERE RegionCode = 'EU'
                """
            )
        )
    ).fetchall()
    existing = {}
    for row in rows:
        payload = {
            "retailer_id": eu_import.row_field(row, "RetailerId"),
            "product_url": eu_import.row_field(row, "ProductUrl"),
            "raw_title": eu_import.row_field(row, "RawProductTitle"),
            "length": eu_import.row_field(row, "LengthFeetInches"),
            "volume": eu_import.row_field(row, "VolumeLitres"),
        }
        inventory_id = int(eu_import.row_field(row, "InventoryId"))
        existing[eu_import.inventory_key(payload)] = inventory_id
        if eu_import.decimal_or_none(payload["volume"]) is None:
            existing[eu_import.inventory_missing_volume_key(payload)] = inventory_id
    return existing


def batch_update_inventory(conn, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute(
        text(
            _sql_region(
                """
                UPDATE dbo.RetailerInventory
                SET BrandId = :brand_id,
                    NormalisedProductTitle = :normalised_title,
                    ProductImageUrl = :product_image_url,
                    PriceAmount = :price_amount,
                    PriceCurrency = 'EUR',
                    StockStatus = :stock_status,
                    Construction = :construction,
                    FinSetup = :fin_setup,
                    LengthFeetInches = :length,
                    Width = :width,
                    Thickness = :thickness,
                    VolumeLitres = :volume,
                    InventoryConfidenceScore = :confidence,
                    LastCheckedUtc = SYSUTCDATETIME(),
                    IsActive = 1,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE InventoryId = :inventory_id
                  AND RegionCode = 'EU'
                """
            )
        ),
        rows,
    )


def batch_insert_inventory(conn, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute(
        text(
            _sql_region(
                """
                INSERT INTO dbo.RetailerInventory (
                    RetailerId,
                    BrandId,
                    BoardModelId,
                    BoardSizeId,
                    RawProductTitle,
                    NormalisedProductTitle,
                    ProductUrl,
                    ProductImageUrl,
                    PriceAud,
                    PriceAmount,
                    PriceCurrency,
                    StockStatus,
                    StockQuantity,
                    Construction,
                    FinSetup,
                    LengthFeetInches,
                    Width,
                    Thickness,
                    VolumeLitres,
                    EstimatedShippingAud,
                    InventoryConfidenceScore,
                    LastCheckedUtc,
                    IsActive,
                    CreatedAtUtc,
                    UpdatedAtUtc,
                    RegionCode
                )
                VALUES (
                    :retailer_id,
                    :brand_id,
                    NULL,
                    NULL,
                    :raw_title,
                    :normalised_title,
                    :product_url,
                    :product_image_url,
                    NULL,
                    :price_amount,
                    'EUR',
                    :stock_status,
                    NULL,
                    :construction,
                    :fin_setup,
                    :length,
                    :width,
                    :thickness,
                    :volume,
                    NULL,
                    :confidence,
                    SYSUTCDATETIME(),
                    1,
                    SYSUTCDATETIME(),
                    SYSUTCDATETIME(),
                    'EU'
                )
                """
            )
        ),
        rows,
    )


def apply_brand_links(conn, brand_updates: list[dict]) -> int:
    if not brand_updates:
        return 0
    conn.execute(
        text(
            _sql_region(
                """
                UPDATE dbo.RetailerInventory
                SET BrandId = :brand_id,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE InventoryId = :inventory_id
                  AND RegionCode = 'EU'
                  AND BrandId IS NULL
                """
            )
        ),
        brand_updates,
    )
    return len(brand_updates)


def apply_model_links(conn, model_updates: list[dict]) -> int:
    if not model_updates:
        return 0
    conn.execute(
        text(
            _sql_region(
                """
                UPDATE dbo.RetailerInventory
                SET BoardModelId = :board_model_id,
                    NormalisedProductTitle = :normalised_title,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE InventoryId = :inventory_id
                  AND RegionCode = 'EU'
                  AND BoardModelId IS NULL
                """
            )
        ),
        model_updates,
    )
    return len(model_updates)


def apply_size_links(conn, size_updates: list[dict]) -> int:
    if not size_updates:
        return 0
    conn.execute(
        text(
            _sql_region(
                """
                UPDATE dbo.RetailerInventory
                SET BoardSizeId = :board_size_id,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE InventoryId = :inventory_id
                  AND RegionCode = 'EU'
                  AND BoardModelId IS NOT NULL
                  AND BoardSizeId IS NULL
                """
            )
        ),
        size_updates,
    )
    return len(size_updates)


def build_apply_rows(report: dict) -> list[dict]:
    rows = []
    for row in report.get("importableRowsForApply", []):
        if row.get("regionCode") != REGION_CODE or row.get("priceCurrency") != PRICE_CURRENCY:
            raise RuntimeError(
                "US apply safety failed: every row must have RegionCode 'US' and PriceCurrency 'USD'."
            )
        rows.append(row)
    return rows


def assert_apply_safety(report: dict) -> None:
    if report.get("regionCode") != REGION_CODE:
        raise RuntimeError("Safety check failed: dry-run regionCode was not US.")
    if report.get("priceCurrency") != PRICE_CURRENCY:
        raise RuntimeError("Safety check failed: dry-run priceCurrency was not USD.")
    sql_counts = report.get("sqlActionCounts", {})
    if sql_counts.get("auRowsTouched") != 0:
        raise RuntimeError("Safety check failed: AU rows touched was not 0.")
    if sql_counts.get("idRowsTouched") != 0:
        raise RuntimeError("Safety check failed: ID rows touched was not 0.")
    if sql_counts.get("inventoryRowsToUpsert", 0) <= 0:
        raise RuntimeError("Safety check failed: no importable US rows were produced.")


def _sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    text_value = str(value).replace("'", "''")
    return f"'{text_value}'"


def snapshot_inventory_rows(conn, inventory_ids: list[int]) -> list[dict]:
    if not inventory_ids:
        return []
    placeholders = ", ".join(str(int(item)) for item in sorted(set(inventory_ids)))
    rows = conn.execute(
        text(
            _sql_region(
                f"""
                SELECT
                    InventoryId,
                    RetailerId,
                    BrandId,
                    BoardModelId,
                    BoardSizeId,
                    NormalisedProductTitle,
                    ProductImageUrl,
                    PriceAmount,
                    PriceCurrency,
                    StockStatus,
                    Construction,
                    FinSetup,
                    LengthFeetInches,
                    Width,
                    Thickness,
                    VolumeLitres,
                    InventoryConfidenceScore,
                    LastCheckedUtc,
                    IsActive
                FROM dbo.RetailerInventory
                WHERE RegionCode = 'EU'
                  AND InventoryId IN ({placeholders})
                """
            )
        )
    ).fetchall()
    return [
        {
            "inventoryId": int(eu_import.row_field(row, "InventoryId")),
            "retailerId": int(eu_import.row_field(row, "RetailerId")),
            "brandId": eu_import.row_field(row, "BrandId"),
            "boardModelId": eu_import.row_field(row, "BoardModelId"),
            "boardSizeId": eu_import.row_field(row, "BoardSizeId"),
            "normalisedProductTitle": eu_import.row_field(row, "NormalisedProductTitle"),
            "productImageUrl": eu_import.row_field(row, "ProductImageUrl"),
            "priceAmount": eu_import.row_field(row, "PriceAmount"),
            "priceCurrency": eu_import.row_field(row, "PriceCurrency"),
            "stockStatus": eu_import.row_field(row, "StockStatus"),
            "construction": eu_import.row_field(row, "Construction"),
            "finSetup": eu_import.row_field(row, "FinSetup"),
            "lengthFeetInches": eu_import.row_field(row, "LengthFeetInches"),
            "width": eu_import.row_field(row, "Width"),
            "thickness": eu_import.row_field(row, "Thickness"),
            "volumeLitres": eu_import.row_field(row, "VolumeLitres"),
            "inventoryConfidenceScore": eu_import.row_field(
                row, "InventoryConfidenceScore"
            ),
            "lastCheckedUtc": eu_import.row_field(row, "LastCheckedUtc"),
            "isActive": eu_import.row_field(row, "IsActive"),
        }
        for row in rows
    ]


def write_rollback_sql(rollback_plan: dict, output_path: Path) -> None:
    lines = [
        "-- USA retailer inventory rollback plan",
        "BEGIN TRANSACTION;",
    ]
    inserted_ids = rollback_plan.get("insertedInventoryIds") or []
    if inserted_ids:
        joined = ", ".join(str(int(item)) for item in sorted(set(inserted_ids)))
        lines.append(
            f"DELETE FROM dbo.RetailerInventory WHERE RegionCode = 'US' AND InventoryId IN ({joined});"
        )

    for row in rollback_plan.get("updatedRowsBefore", []):
        lines.append(
            "UPDATE dbo.RetailerInventory SET "
            f"RetailerId = {_sql_literal(row.get('retailerId'))}, "
            f"BrandId = {_sql_literal(row.get('brandId'))}, "
            f"BoardModelId = {_sql_literal(row.get('boardModelId'))}, "
            f"BoardSizeId = {_sql_literal(row.get('boardSizeId'))}, "
            f"NormalisedProductTitle = {_sql_literal(row.get('normalisedProductTitle'))}, "
            f"ProductImageUrl = {_sql_literal(row.get('productImageUrl'))}, "
            f"PriceAmount = {_sql_literal(row.get('priceAmount'))}, "
            f"PriceCurrency = {_sql_literal(row.get('priceCurrency'))}, "
            f"StockStatus = {_sql_literal(row.get('stockStatus'))}, "
            f"Construction = {_sql_literal(row.get('construction'))}, "
            f"FinSetup = {_sql_literal(row.get('finSetup'))}, "
            f"LengthFeetInches = {_sql_literal(row.get('lengthFeetInches'))}, "
            f"Width = {_sql_literal(row.get('width'))}, "
            f"Thickness = {_sql_literal(row.get('thickness'))}, "
            f"VolumeLitres = {_sql_literal(row.get('volumeLitres'))}, "
            f"InventoryConfidenceScore = {_sql_literal(row.get('inventoryConfidenceScore'))}, "
            f"LastCheckedUtc = {_sql_literal(row.get('lastCheckedUtc'))}, "
            f"IsActive = {_sql_literal(row.get('isActive'))}, "
            "UpdatedAtUtc = SYSUTCDATETIME() "
            f"WHERE RegionCode = 'US' AND InventoryId = {int(row['inventoryId'])};"
        )

    inserted_retailers = rollback_plan.get("insertedRetailerIds") or []
    if inserted_retailers:
        joined = ", ".join(str(int(item)) for item in sorted(set(inserted_retailers)))
        lines.append(
            "DELETE FROM dbo.Retailers "
            f"WHERE RegionCode = 'US' AND RetailerId IN ({joined}) "
            "AND NOT EXISTS ("
            "SELECT 1 FROM dbo.RetailerInventory ri "
            "WHERE ri.RetailerId = dbo.Retailers.RetailerId AND ri.RegionCode = 'US'"
            ");"
        )

    lines.append("COMMIT TRANSACTION;")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_to_sql(
    report: dict,
    output_file: Path,
    rollback_output_file: Path = ROLLBACK_PLAN_FILE,
    rollback_sql_output_file: Path = ROLLBACK_SQL_FILE,
) -> dict:
    assert_apply_safety(report)
    rows = build_apply_rows(report)
    engine = eu_import.build_engine()
    apply_counts = Counter()

    with eu_import.begin_with_retry(engine) as conn:
        eu_import.assert_schema(conn)
        before = {
            "usInventoryRows": eu_import.count_inventory_by_region(conn, "US"),
            "usRetailers": eu_import.count_retailers_by_region(conn, "US"),
            "auInventoryRows": eu_import.count_inventory_by_region(conn, "AU"),
            "euInventoryRows": eu_import.count_inventory_by_region(conn, "EU"),
            "idInventoryRows": eu_import.count_inventory_by_region(conn, "ID"),
        }
        retailer_counts_before = priority_retailer_counts(conn)
        brands = eu_import.brand_lookup(conn)
        retailer_ids: dict[str, int] = {}
        inserted_retailer_ids: list[int] = []

        retailer_payloads: dict[str, dict] = {}
        for row in rows:
            slug = eu_import.clean(row.get("retailerSlug"))
            if slug not in retailer_payloads:
                retailer_payloads[slug] = {
                    "retailer_name": eu_import.clean(row.get("retailerName")),
                    "website_url": eu_import.website_from_product_url(
                        row.get("productUrl")
                    ),
                    "country": eu_import.clean(row.get("country")) or "United States",
                }

        for slug, retailer in retailer_payloads.items():
            retailer_id, created = get_or_create_retailer(conn, retailer)
            retailer_ids[slug] = retailer_id
            if created:
                inserted_retailer_ids.append(retailer_id)
            apply_counts["retailersInserted" if created else "retailersUpdated"] += 1

        existing_inventory = load_existing_us_inventory(conn)
        insert_rows = []
        update_rows = []
        for row in rows:
            retailer_slug = eu_import.clean(row.get("retailerSlug"))
            retailer_id = retailer_ids.get(retailer_slug)
            if retailer_id is None:
                apply_counts["rowsSkippedMissingRetailer"] += 1
                continue

            matched_brand = eu_import.clean(row.get("matchedBrandName"))
            brand_id = brands.get(eu_import.clean_key(matched_brand)) if matched_brand else None
            payload = {
                "retailer_id": retailer_id,
                "brand_id": brand_id,
                "raw_title": eu_import.clean(row.get("rawProductTitle"))
                or "Unknown US surfboard",
                "normalised_title": eu_import.clean(row.get("modelName"))
                or eu_import.clean(row.get("rawProductTitle")),
                "product_url": eu_import.clean(row.get("productUrl")),
                "product_image_url": eu_import.clean(row.get("productImageUrl")),
                "price_amount": eu_import.decimal_or_none(row.get("priceAmount")),
                "stock_status": eu_import.import_stock_status(row),
                "construction": eu_import.clean(row.get("construction")),
                "fin_setup": eu_import.clean(row.get("finSetup")),
                "length": eu_import.clean(row.get("lengthFeetInches")),
                "width": eu_import.clean(row.get("width")),
                "thickness": eu_import.clean(row.get("thickness")),
                "volume": eu_import.decimal_or_none(row.get("volumeLitres")),
                "confidence": row.get("parseConfidence") or 0,
            }
            payload = conform_inventory_payload_for_sql(payload)
            inventory_id = existing_inventory.get(eu_import.inventory_key(payload))
            if inventory_id is None and payload["volume"] is not None:
                inventory_id = existing_inventory.get(
                    eu_import.inventory_missing_volume_key(payload)
                )
            if inventory_id is None:
                insert_rows.append(payload)
            else:
                update_rows.append({**payload, "inventory_id": inventory_id})

        updated_rows_before = snapshot_inventory_rows(
            conn, [row["inventory_id"] for row in update_rows]
        )

        batch_insert_inventory(conn, insert_rows)
        batch_update_inventory(conn, update_rows)
        apply_counts["inventoryRowsInserted"] = len(insert_rows)
        apply_counts["inventoryRowsUpdated"] = len(update_rows)

        eu_import.load_eu_inventory_rows = load_us_inventory_rows
        link_report_before = eu_import.build_canonical_link_report(conn)
        brand_links_applied = apply_brand_links(conn, link_report_before["brandUpdates"])
        model_links_applied = apply_model_links(conn, link_report_before["modelUpdates"])
        size_links_applied = apply_size_links(conn, link_report_before["sizeUpdates"])
        apply_counts["brandLinksApplied"] = brand_links_applied
        apply_counts["modelLinksApplied"] = model_links_applied
        apply_counts["sizeLinksApplied"] = size_links_applied
        link_report_after = eu_import.build_canonical_link_report(conn)

        after = {
            "usInventoryRows": eu_import.count_inventory_by_region(conn, "US"),
            "usRetailers": eu_import.count_retailers_by_region(conn, "US"),
            "auInventoryRows": eu_import.count_inventory_by_region(conn, "AU"),
            "euInventoryRows": eu_import.count_inventory_by_region(conn, "EU"),
            "idInventoryRows": eu_import.count_inventory_by_region(conn, "ID"),
        }
        retailer_counts_after = priority_retailer_counts(conn)
        if after["auInventoryRows"] != before["auInventoryRows"]:
            raise RuntimeError(
                "US import safety failed: AU inventory count changed; transaction rolled back."
            )
        if after["euInventoryRows"] != before["euInventoryRows"]:
            raise RuntimeError(
                "US import safety failed: EU inventory count changed; transaction rolled back."
            )
        if after["idInventoryRows"] != before["idInventoryRows"]:
            raise RuntimeError(
                "US import safety failed: ID inventory count changed; transaction rolled back."
            )
        samples = sample_us_rows(conn)
        existing_after = load_existing_us_inventory(conn)
        inserted_inventory_ids = [
            existing_after[key]
            for key in (eu_import.inventory_key(row) for row in insert_rows)
            if key in existing_after
        ]

    rollback_plan = {
        "regionCode": REGION_CODE,
        "insertedRetailerIds": inserted_retailer_ids,
        "insertedInventoryIds": inserted_inventory_ids,
        "updatedRowsBefore": updated_rows_before,
    }
    rollback_plan = to_json_safe(rollback_plan)
    rollback_output_file.parent.mkdir(parents=True, exist_ok=True)
    rollback_output_file.write_text(
        json.dumps(rollback_plan, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_rollback_sql(rollback_plan, rollback_sql_output_file)

    validation = {
        "auRowsReduced": after["auInventoryRows"] < before["auInventoryRows"],
        "euRowsReduced": after["euInventoryRows"] < before["euInventoryRows"],
        "idRowsReduced": after["idInventoryRows"] < before["idInventoryRows"],
        "auRowsTouched": 0,
        "euRowsTouched": 0,
        "idRowsTouched": 0,
        "allWritesRegionCode": REGION_CODE,
        "rollbackPlanWritten": True,
        "rollbackSqlWritten": True,
    }
    apply_report = {
        **report,
        "mode": "apply",
        "applyRequested": True,
        "purpose": "US RetailerInventory import apply. Scoped to RegionCode US and idempotent upserts.",
        "applyCounts": dict(apply_counts),
        "beforeCounts": before,
        "afterCounts": after,
        "retailerCountsBefore": retailer_counts_before,
        "retailerCountsAfter": retailer_counts_after,
        "validation": validation,
        "canonicalLinkingBeforeApply": eu_import.public_link_report(link_report_before),
        "canonicalLinkingAfterApply": eu_import.public_link_report(link_report_after),
        "sampleUsRows": samples,
        "rollbackPlanFile": str(rollback_output_file),
        "rollbackSqlFile": str(rollback_sql_output_file),
    }
    apply_report = to_json_safe(apply_report)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(apply_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    eu_import.write_link_report(link_report_after, LINK_REPORT_FILE)
    return apply_report


def build_report(rows: list[dict], input_file: Path, retailer_slug: str = "") -> dict:
    projected_rows = []
    for row in rows:
        projected = dict(row)
        brand, model, _ = normalise_brand_and_model_for_projection(projected)
        if brand:
            projected["brandName"] = brand
        if model:
            projected["modelName"] = model
        if excluded_product_type(projected):
            projected.setdefault("projectionNotes", []).append("excluded_from_projected_canonical_linking")
        projected_rows.append(projected)

    report = eu_import.build_report(projected_rows, input_file, retailer_slug)
    report["purpose"] = "US RetailerInventory import dry-run only. No SQL writes."
    report["regionCode"] = REGION_CODE
    report["priceCurrency"] = PRICE_CURRENCY
    report["applySafetyNotes"] = [
        "Dry-run is the default and does not connect to SQL.",
        "Any future --apply must keep WHERE RegionCode = 'US' on updates/deactivations.",
        "AU, EU, and ID rows must never be updated by this importer.",
        "Guarded apply requires the explicit --confirm-apply-us token.",
    ]
    return report


def export_import_sql(report: dict, output_file: Path) -> None:
    report = dict(report)
    report["regionCode"] = REGION_CODE
    report["priceCurrency"] = PRICE_CURRENCY
    eu_import.export_import_sql(report, output_file)
    sql_text = output_file.read_text(encoding="utf-8")
    sql_text = sql_text.replace("'EU'", "'US'").replace("'EUR'", "'USD'")
    sql_text = sql_text.replace("RegionCode EU", "RegionCode US")
    sql_text = sql_text.replace("-- Quivrr EU retailer inventory import", "-- Quivrr US retailer inventory import")
    sql_text = sql_text.replace("-- Scope: EU only. No AU or ID writes.", "-- Scope: US only. No AU, EU, or ID writes.")
    output_file.write_text(sql_text, encoding="utf-8")


def main() -> None:
    configure_eu_base()
    parser = argparse.ArgumentParser(
        description="US retailer inventory importer. Dry-run by default."
    )
    parser.add_argument("--input", default=str(INPUT_FILE))
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    parser.add_argument("--apply-output", default=str(APPLY_OUTPUT_FILE))
    parser.add_argument("--retailer", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--confirm-apply-us",
        default="",
        help=f"Required confirmation token for live US apply: {CONFIRM_TOKEN}",
    )
    parser.add_argument("--schema-check", action="store_true")
    parser.add_argument("--link-tests", action="store_true")
    parser.add_argument("--apply-links", action="store_true")
    parser.add_argument("--link-apply-output", default=str(LINK_APPLY_REPORT_FILE))
    parser.add_argument("--export-sql", action="store_true")
    parser.add_argument("--sql-output", default=str(SQL_OUTPUT_FILE))
    parser.add_argument("--azure-run", action="store_true")
    parser.add_argument("--rollback-output", default=str(ROLLBACK_PLAN_FILE))
    parser.add_argument("--rollback-sql-output", default=str(ROLLBACK_SQL_FILE))
    args = parser.parse_args()

    eu_import.priority_retailer_counts = priority_retailer_counts
    eu_import.sample_eu_rows = sample_us_rows
    eu_import.load_eu_inventory_rows = load_us_inventory_rows

    emit_event(
        "inventory_import_started",
        "retailer_inventory",
        region=REGION_CODE,
        status="success",
    )

    if args.link_tests:
        result = eu_import.run_link_tests()
        print("US canonical linker tests complete")
        print(f"Tests run: {result['testsRun']}")
        print(f"Tests passed: {result['testsPassed']}")
        if result["failures"]:
            print(json.dumps(result["failures"], indent=2))
            raise RuntimeError("Canonical linker tests failed.")
        return

    if args.schema_check:
        raise RuntimeError("Local SQL schema checks are disabled. Run schema checks from Azure.")

    if args.apply_links:
        raise RuntimeError(
            "US apply-links is reserved for post-import SQL access and was not run locally."
        )

    if args.azure_run:
        print("Local Azure SQL execution is disabled.")
        print("Run from an approved Azure environment instead, for example:")
        print(
            "venv\\Scripts\\python.exe scripts/usa/import_us_retailer_inventory.py "
            f"--apply --confirm-apply-us {CONFIRM_TOKEN}"
        )
        return

    input_file = Path(args.input)
    output_file = Path(args.output)
    rows = eu_import.load_input_rows(input_file, args.retailer)
    report = build_report(rows, input_file, args.retailer)

    if args.apply:
        if args.confirm_apply_us != CONFIRM_TOKEN:
            raise RuntimeError(
                "US apply mode requires explicit confirmation via "
                f"--confirm-apply-us {CONFIRM_TOKEN}."
            )
        apply_report = apply_to_sql(
            report,
            Path(args.apply_output),
            rollback_output_file=Path(args.rollback_output),
            rollback_sql_output_file=Path(args.rollback_sql_output),
        )
        emit_event(
            "inventory_import_completed",
            "retailer_inventory",
            region=REGION_CODE,
            status="success",
            rows_loaded=report["metrics"]["importableRows"],
            rows_inserted=apply_report["applyCounts"].get("inventoryRowsInserted"),
        )
        update_job_state(
            "inventory_us",
            "inventory",
            "retailer_inventory",
            "success",
            region=REGION_CODE,
            rows_loaded=report["metrics"]["importableRows"],
            rows_inserted=apply_report["applyCounts"].get("inventoryRowsInserted"),
        )
        print("US retailer inventory apply complete")
        print(f"Before region counts: {apply_report['beforeCounts']}")
        print(f"After region counts: {apply_report['afterCounts']}")
        print(f"Rollback plan: {apply_report['rollbackPlanFile']}")
        print(f"Rollback SQL: {apply_report['rollbackSqlFile']}")
        return

    if args.export_sql:
        export_import_sql(report, Path(args.sql_output))
        print("US retailer import SQL export complete")
        print(f"Rows after dedupe: {report['rowsAfterDedupe']}")
        print(f"Importable rows: {report['metrics']['importableRows']}")
        print(f"SQL output: {args.sql_output}")
        return

    report["canonicalLinking"] = {
        "status": "estimated_only",
        "reason": "Local dry-run uses catalogue readiness only. Live SQL linking requires approved Azure SQL access.",
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    emit_event(
        "inventory_import_completed",
        "retailer_inventory",
        region=REGION_CODE,
        status="success",
        rows_loaded=report["metrics"]["importableRows"],
    )
    update_job_state(
        "inventory_us",
        "inventory",
        "retailer_inventory",
        "success",
        region=REGION_CODE,
        rows_loaded=report["metrics"]["importableRows"],
    )
    print("US retailer inventory dry-run complete")
    print(f"Rows after dedupe: {report['rowsAfterDedupe']}")
    print(f"Importable rows: {report['metrics']['importableRows']}")
    print(f"Rejected rows: {report['metrics']['rejectedRows']}")
    print(f"Recommendation: {report['recommendation']}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit_event(
            "inventory_import_failed",
            "retailer_inventory",
            region=REGION_CODE,
            status="failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        update_job_state(
            "inventory_us",
            "inventory",
            "retailer_inventory",
            "failed",
            region=REGION_CODE,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise
