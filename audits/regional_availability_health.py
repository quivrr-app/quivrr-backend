from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import text

from audits.common import (
    REGIONS,
    available_status_sql,
    available_stock_status,
    normalize_brand_name,
    resolve_supported_brands,
    row_to_dict,
)
from market_intelligence.db import execute_with_retry


FALLBACK_REASON_ORDER = (
    "inactive",
    "missing_product_url",
    "unsupported_stock_status",
    "missing_brand_id",
    "eligible",
)


def fallback_primary_reason(row: dict[str, Any]) -> str:
    if not bool(row.get("IsActive")):
        return "inactive"
    if not str(row.get("ProductUrl") or "").strip():
        return "missing_product_url"
    if not available_stock_status(row.get("StockStatus")):
        return "unsupported_stock_status"
    if row.get("BrandId") is None:
        return "missing_brand_id"
    return "eligible"


def summarize_fallback_exclusions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    primary_reason_counts = Counter()
    multi_reason_counts = Counter()
    for row in rows:
        reasons = []
        if not bool(row.get("IsActive")):
            reasons.append("inactive")
        if not str(row.get("ProductUrl") or "").strip():
            reasons.append("missing_product_url")
        if not available_stock_status(row.get("StockStatus")):
            reasons.append("unsupported_stock_status")
        if row.get("BrandId") is None:
            reasons.append("missing_brand_id")
        if not reasons:
            reasons = ["eligible"]
        primary_reason_counts[reasons[0]] += 1
        for reason in reasons:
            multi_reason_counts[reason] += 1
    return {
        "rowsReviewed": len(rows),
        "primaryReasonCounts": {
            reason: int(primary_reason_counts.get(reason, 0))
            for reason in FALLBACK_REASON_ORDER
            if primary_reason_counts.get(reason, 0)
        },
        "allReasonCounts": dict(sorted(multi_reason_counts.items())),
    }


def build_regional_availability_health_report() -> dict[str, Any]:
    brand_entries = resolve_supported_brands()
    canonical_models = [
        row_to_dict(row)
        for row in execute_with_retry(
            text(
                """
                SELECT bm.BoardModelId, bm.BrandId
                FROM dbo.BoardModels bm
                WHERE bm.IsActive = 1
                """
            )
        )
    ]
    canonical_models_by_brand: dict[int, set[int]] = defaultdict(set)
    for row in canonical_models:
        canonical_models_by_brand[int(row["BrandId"])].add(int(row["BoardModelId"]))

    retailer_rows = [
        row_to_dict(row)
        for row in execute_with_retry(
            text(
                f"""
                SELECT
                    ri.RegionCode,
                    b.BrandName,
                    COUNT(*) AS RetailerActiveRows,
                    SUM(CASE WHEN {available_status_sql('ri.StockStatus')} THEN 1 ELSE 0 END) AS RetailerAvailableRows,
                    SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS RetailerLinkedModelRows,
                    SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS RetailerLinkedSizeRows,
                    COUNT(DISTINCT CASE WHEN ri.BoardModelId IS NOT NULL AND {available_status_sql('ri.StockStatus')} THEN ri.BoardModelId END) AS ModelsWithRetailerStock,
                    COUNT(DISTINCT CASE WHEN ri.BoardModelId IS NOT NULL AND {available_status_sql('ri.StockStatus')} AND ri.ProductUrl IS NOT NULL THEN ri.BoardModelId END) AS FallbackEligibleModels,
                    SUM(CASE WHEN {available_status_sql('ri.StockStatus')} AND ri.ProductUrl IS NOT NULL THEN 1 ELSE 0 END) AS FallbackEligibleRows,
                    SUM(CASE WHEN ri.BoardModelId IS NOT NULL AND ri.LengthFeetInches IS NOT NULL AND {available_status_sql('ri.StockStatus')} AND ri.ProductUrl IS NOT NULL THEN 1 ELSE 0 END) AS CloseEligibleRows,
                    MAX(COALESCE(ri.LastCheckedUtc, ri.UpdatedAtUtc, ri.CreatedAtUtc)) AS LatestRetailerRefreshUtc
                FROM dbo.RetailerInventory ri
                LEFT JOIN dbo.Brands b
                    ON b.BrandId = ri.BrandId
                WHERE ri.IsActive = 1
                GROUP BY ri.RegionCode, b.BrandName
                """
            )
        )
    ]
    manufacturer_rows = [
        row_to_dict(row)
        for row in execute_with_retry(
            text(
                """
                SELECT
                    mi.RegionCode,
                    b.BrandName,
                    COUNT(*) AS ManufacturerActiveRows,
                    SUM(CASE WHEN COALESCE(mi.IsAvailable, 0) = 1 THEN 1 ELSE 0 END) AS ManufacturerAvailableRows,
                    SUM(CASE WHEN mi.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS ManufacturerLinkedModelRows,
                    SUM(CASE WHEN mi.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS ManufacturerLinkedSizeRows,
                    COUNT(DISTINCT CASE WHEN mi.BoardModelId IS NOT NULL AND COALESCE(mi.IsAvailable, 0) = 1 THEN mi.BoardModelId END) AS ModelsWithManufacturerStock,
                    MAX(COALESCE(mi.ScrapedAtUtc, mi.UpdatedAtUtc, mi.CreatedAtUtc)) AS LatestManufacturerRefreshUtc
                FROM dbo.ManufacturerInventory mi
                LEFT JOIN dbo.Brands b
                    ON b.BrandId = mi.BrandId
                WHERE COALESCE(mi.IsActive, 1) = 1
                GROUP BY mi.RegionCode, b.BrandName
                """
            )
        )
    ]
    retailer_model_id_rows = [
        row_to_dict(row)
        for row in execute_with_retry(
            text(
                f"""
                SELECT DISTINCT
                    ri.RegionCode,
                    b.BrandName,
                    ri.BoardModelId
                FROM dbo.RetailerInventory ri
                LEFT JOIN dbo.Brands b
                    ON b.BrandId = ri.BrandId
                WHERE ri.IsActive = 1
                  AND ri.BoardModelId IS NOT NULL
                  AND {available_status_sql('ri.StockStatus')}
                """
            )
        )
    ]
    manufacturer_model_id_rows = [
        row_to_dict(row)
        for row in execute_with_retry(
            text(
                """
                SELECT DISTINCT
                    mi.RegionCode,
                    b.BrandName,
                    mi.BoardModelId
                FROM dbo.ManufacturerInventory mi
                LEFT JOIN dbo.Brands b
                    ON b.BrandId = mi.BrandId
                WHERE COALESCE(mi.IsActive, 1) = 1
                  AND COALESCE(mi.IsAvailable, 0) = 1
                  AND mi.BoardModelId IS NOT NULL
                """
            )
        )
    ]
    retailer_lookup = {
        (str(row.get("RegionCode") or "").upper(), normalize_brand_name(row.get("BrandName"))): row
        for row in retailer_rows
    }
    manufacturer_lookup = {
        (str(row.get("RegionCode") or "").upper(), normalize_brand_name(row.get("BrandName"))): row
        for row in manufacturer_rows
    }
    retailer_model_ids_lookup: dict[tuple[str, str], set[int]] = defaultdict(set)
    manufacturer_model_ids_lookup: dict[tuple[str, str], set[int]] = defaultdict(set)
    for row in retailer_model_id_rows:
        region_brand_key = (
            str(row.get("RegionCode") or "").upper(),
            normalize_brand_name(row.get("BrandName")),
        )
        if row.get("BoardModelId") is not None:
            retailer_model_ids_lookup[region_brand_key].add(int(row["BoardModelId"]))
    for row in manufacturer_model_id_rows:
        region_brand_key = (
            str(row.get("RegionCode") or "").upper(),
            normalize_brand_name(row.get("BrandName")),
        )
        if row.get("BoardModelId") is not None:
            manufacturer_model_ids_lookup[region_brand_key].add(int(row["BoardModelId"]))
    region_brand_rows = []
    for region in REGIONS:
        for brand_entry in brand_entries:
            display_name = brand_entry["displayName"]
            retailer = retailer_lookup.get((region, display_name), {})
            manufacturer = manufacturer_lookup.get((region, display_name), {})
            canonical_model_ids = {
                model_id
                for brand_id in brand_entry["brandIds"]
                for model_id in canonical_models_by_brand.get(brand_id, set())
            }
            retailer_model_ids = retailer_model_ids_lookup.get((region, display_name), set())
            manufacturer_model_ids = manufacturer_model_ids_lookup.get((region, display_name), set())
            models_with_retailer_stock = len(retailer_model_ids)
            models_with_manufacturer_stock = len(manufacturer_model_ids)
            models_with_any_stock = len(retailer_model_ids | manufacturer_model_ids)
            region_brand_rows.append(
                {
                    "region": region,
                    "brandName": display_name,
                    "retailerActiveRows": int(retailer.get("RetailerActiveRows") or 0),
                    "retailerAvailableRows": int(retailer.get("RetailerAvailableRows") or 0),
                    "retailerLinkedModelRows": int(retailer.get("RetailerLinkedModelRows") or 0),
                    "retailerLinkedSizeRows": int(retailer.get("RetailerLinkedSizeRows") or 0),
                    "manufacturerActiveRows": int(manufacturer.get("ManufacturerActiveRows") or 0),
                    "manufacturerAvailableRows": int(manufacturer.get("ManufacturerAvailableRows") or 0),
                    "manufacturerLinkedModelRows": int(manufacturer.get("ManufacturerLinkedModelRows") or 0),
                    "manufacturerLinkedSizeRows": int(manufacturer.get("ManufacturerLinkedSizeRows") or 0),
                    "modelsWithRetailerStock": models_with_retailer_stock,
                    "modelsWithManufacturerStock": models_with_manufacturer_stock,
                    "modelsWithAnyStock": models_with_any_stock,
                    "canonicalModelsWithNoStock": max(0, len(canonical_model_ids) - models_with_any_stock),
                    "fallbackEligibleRows": int(retailer.get("FallbackEligibleRows") or 0),
                    "fallbackEligibleModels": int(retailer.get("FallbackEligibleModels") or 0),
                    "closeEligibleRows": int(retailer.get("CloseEligibleRows") or 0),
                    "latestRetailerRefreshUtc": retailer.get("LatestRetailerRefreshUtc"),
                    "latestManufacturerRefreshUtc": manufacturer.get("LatestManufacturerRefreshUtc"),
                }
            )

    au_album_row_details = [
        row_to_dict(row)
        for row in execute_with_retry(
            text(
                """
                SELECT
                    ri.InventoryId,
                    ri.IsActive,
                    ri.StockStatus,
                    ri.ProductUrl,
                    ri.BrandId,
                    ri.BoardModelId,
                    ri.BoardSizeId,
                    ri.RegionCode,
                    b.BrandName,
                    ri.RawProductTitle
                FROM dbo.RetailerInventory ri
                LEFT JOIN dbo.Brands b
                    ON b.BrandId = ri.BrandId
                WHERE ri.RegionCode = 'AU'
                  AND (
                    b.BrandName = 'Album'
                  )
                """
            )
        )
    ]
    au_album_active_rows = [row for row in au_album_row_details if bool(row.get("IsActive"))]
    au_album_available_rows = [row for row in au_album_active_rows if available_stock_status(row.get("StockStatus"))]
    au_album_with_product_url = [row for row in au_album_active_rows if str(row.get("ProductUrl") or "").strip()]
    au_album_fallback_summary = summarize_fallback_exclusions(au_album_row_details)

    return {
        "regions": region_brand_rows,
        "focus": {
            "AU Album": {
                "retailerRowsTotal": len(au_album_row_details),
                "retailerRowsActive": len(au_album_active_rows),
                "retailerRowsAvailable": len(au_album_available_rows),
                "retailerRowsWithProductUrl": len(au_album_with_product_url),
                "fallbackExclusionSummary": au_album_fallback_summary,
                "fallbackEligibleRows": int(
                    sum(1 for row in au_album_row_details if fallback_primary_reason(row) == "eligible")
                ),
                "sampleTitles": [
                    str(row.get("RawProductTitle") or "")
                    for row in au_album_row_details[:10]
                ],
            }
        },
        "summary": {
            "regionBrandRows": len(region_brand_rows),
            "brandsWithZeroRetailerStock": [
                {
                    "region": row["region"],
                    "brandName": row["brandName"],
                }
                for row in region_brand_rows
                if row["retailerActiveRows"] == 0
            ],
        },
    }
