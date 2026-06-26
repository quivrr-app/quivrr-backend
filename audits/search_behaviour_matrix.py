from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import app as backend_app
from sqlalchemy import text

from audits.common import REGIONS, SUPPORTED_BRANDS, available_status_sql, normalize_brand_name, resolve_supported_brands, row_to_dict
from market_intelligence.db import execute_with_retry

DEFAULT_MAX_AUTO_CASES = int(os.getenv("SEARCH_AUDIT_MAX_AUTO_CASES", "32"))


@dataclass(frozen=True)
class SearchCase:
    region: str
    board_size_id: int
    brand: str
    model: str
    construction: str | None
    length: str | None
    label: str


def search_case_result(
    case: SearchCase,
    search_payload: dict[str, Any],
    fallback_candidate_count: int,
    close_candidate_count: int,
) -> dict[str, Any]:
    direct_count = len(search_payload.get("directManufacturerMatches") or [])
    exact_count = len(search_payload.get("exactRetailerMatches") or [])
    close_count = len(search_payload.get("closeRetailerMatches") or [])
    other_count = len(search_payload.get("otherModelMatches") or [])
    expected_fallback = (
        direct_count == 0
        and exact_count == 0
        and close_count < 3
        and (fallback_candidate_count > 0 or other_count > 0)
    )
    expected_close = exact_count == 0 and close_candidate_count > 0
    mismatch_reason = None
    if expected_fallback and other_count == 0:
        mismatch_reason = "fallback_expected_but_not_returned"
    elif not expected_fallback and other_count > 0:
        mismatch_reason = "fallback_returned_when_not_expected"
    elif expected_close and close_count == 0:
        mismatch_reason = "close_matches_expected_but_not_returned"

    return {
        "label": case.label,
        "region": case.region,
        "brand": case.brand,
        "model": case.model,
        "construction": case.construction,
        "length": case.length,
        "boardSizeId": case.board_size_id,
        "directCount": direct_count,
        "exactCount": exact_count,
        "closeCount": close_count,
        "otherModelCount": other_count,
        "searchVersion": search_payload.get("searchVersion"),
        "expectedFallback": expected_fallback,
        "actualFallback": other_count > 0,
        "expectedClose": expected_close,
        "actualClose": close_count > 0,
        "fallbackCandidateCount": fallback_candidate_count,
        "closeCandidateCount": close_candidate_count,
        "reasonIfMismatch": mismatch_reason,
    }


def _fetch_board_size_id(brand_name: str, model_name: str, length: str | None = None) -> tuple[int | None, str | None]:
    params: dict[str, Any] = {
        "brand_name": brand_name,
        "model_name": model_name,
    }
    length_clause = ""
    if length:
        length_clause = "AND bs.LengthFeetInches = :length"
        params["length"] = length
    rows = execute_with_retry(
        text(
            f"""
            SELECT TOP 1
                bs.BoardSizeId,
                bs.Construction
            FROM dbo.BoardSizes bs
            INNER JOIN dbo.BoardModels bm
                ON bm.BoardModelId = bs.BoardModelId
            INNER JOIN dbo.Brands b
                ON b.BrandId = bm.BrandId
            WHERE bm.IsActive = 1
              AND b.BrandName = :brand_name
              AND bm.ModelName = :model_name
              {length_clause}
            ORDER BY
                CASE WHEN bs.VolumeLitres IS NULL THEN 1 ELSE 0 END,
                bs.VolumeLitres ASC,
                bs.LengthFeetInches ASC
            """
        ),
        params,
    )
    if not rows:
        return None, None
    row = row_to_dict(rows[0])
    return int(row["BoardSizeId"]), row.get("Construction")


def _build_seed_cases() -> list[SearchCase]:
    selectors = [
        ("AU", "Album", "Bom Dia", None, "AU Album Bom Dia smallest available canonical size"),
        ("AU", "Album", "Bom Dia", "5'7", "AU Album Bom Dia 5'7"),
        ("AU", "Rusty", "1984", "5'8", "AU Rusty 1984"),
        ("US", "Album", "Bom Dia", "5'7", "US Album Bom Dia"),
        ("US", "Pyzel", "Happy Twin", None, "US Pyzel Happy Twin"),
        ("US", None, None, None, "US exact suppression case BoardSizeId 184752"),
        ("EU", "Album", "Bom Dia", "5'7", "EU Album Bom Dia"),
        ("ID", "Album", "Bom Dia", "5'7", "ID Album Bom Dia"),
    ]
    cases: list[SearchCase] = []
    for region, brand, model, length, label in selectors:
        if label == "US exact suppression case BoardSizeId 184752":
            cases.append(
                SearchCase(
                    region="US",
                    board_size_id=184752,
                    brand="Unknown",
                    model="Unknown",
                    construction=None,
                    length=None,
                    label=label,
                )
            )
            continue
        board_size_id, construction = _fetch_board_size_id(brand, model, length)
        if board_size_id is None:
            continue
        cases.append(
            SearchCase(
                region=region,
                board_size_id=board_size_id,
                brand=brand,
                model=model,
                construction=construction,
                length=length,
                label=label,
            )
        )
    return cases


def _sample_cases() -> list[SearchCase]:
    brand_names_sql = ", ".join("'" + brand.replace("'", "''") + "'" for brand in SUPPORTED_BRANDS)
    region_values_sql = ", ".join(f"('{region}')" for region in REGIONS)
    exact_rows = execute_with_retry(
        text(
            f"""
            WITH ranked AS (
                SELECT
                    ri.RegionCode,
                    b.BrandName,
                    bm.ModelName,
                    ri.BoardSizeId,
                    ri.LengthFeetInches,
                    bs.Construction,
                    ROW_NUMBER() OVER (
                        PARTITION BY ri.RegionCode, b.BrandName
                        ORDER BY ri.InventoryId DESC
                    ) AS rn
                FROM dbo.RetailerInventory ri
                INNER JOIN dbo.BoardModels bm
                    ON bm.BoardModelId = ri.BoardModelId
                INNER JOIN dbo.Brands b
                    ON b.BrandId = bm.BrandId
                LEFT JOIN dbo.BoardSizes bs
                    ON bs.BoardSizeId = ri.BoardSizeId
                WHERE ri.IsActive = 1
                  AND ri.BoardSizeId IS NOT NULL
                  AND ({available_status_sql('ri.StockStatus')})
                  AND b.BrandName IN ({brand_names_sql})
            )
            SELECT *
            FROM ranked
            WHERE rn = 1
            """
        )
    )
    close_rows = execute_with_retry(
        text(
            f"""
            WITH candidate_models AS (
                SELECT
                    ri.RegionCode,
                    b.BrandName,
                    ri.BoardModelId
                FROM dbo.RetailerInventory ri
                INNER JOIN dbo.BoardModels bm
                    ON bm.BoardModelId = ri.BoardModelId
                INNER JOIN dbo.Brands b
                    ON b.BrandId = bm.BrandId
                WHERE ri.IsActive = 1
                  AND ({available_status_sql('ri.StockStatus')})
                  AND ri.BoardSizeId IS NOT NULL
                  AND b.BrandName IN ({brand_names_sql})
                GROUP BY ri.RegionCode, b.BrandName, ri.BoardModelId
                HAVING COUNT(DISTINCT ri.BoardSizeId) >= 2
            ),
            ranked AS (
                SELECT
                    ri.RegionCode,
                    b.BrandName,
                    bm.ModelName,
                    ri.BoardSizeId,
                    ri.LengthFeetInches,
                    bs.Construction,
                    ROW_NUMBER() OVER (
                        PARTITION BY ri.RegionCode, b.BrandName
                        ORDER BY ri.InventoryId DESC
                    ) AS rn
                FROM dbo.RetailerInventory ri
                INNER JOIN candidate_models cm
                    ON cm.RegionCode = ri.RegionCode
                   AND cm.BrandName = (SELECT BrandName FROM dbo.Brands WHERE BrandId = ri.BrandId)
                   AND cm.BoardModelId = ri.BoardModelId
                INNER JOIN dbo.BoardModels bm
                    ON bm.BoardModelId = ri.BoardModelId
                INNER JOIN dbo.Brands b
                    ON b.BrandId = bm.BrandId
                LEFT JOIN dbo.BoardSizes bs
                    ON bs.BoardSizeId = ri.BoardSizeId
                WHERE ri.IsActive = 1
                  AND ({available_status_sql('ri.StockStatus')})
                  AND ri.BoardSizeId IS NOT NULL
            )
            SELECT *
            FROM ranked
            WHERE rn = 1
            """
        )
    )
    no_stock_rows = execute_with_retry(
        text(
            f"""
            WITH regions AS (
                SELECT region_code
                FROM (VALUES {region_values_sql}) AS source(region_code)
            ),
            ranked AS (
                SELECT
                    regions.region_code AS RegionCode,
                    b.BrandName,
                    bm.ModelName,
                    bs.BoardSizeId,
                    bs.LengthFeetInches,
                    bs.Construction,
                    ROW_NUMBER() OVER (
                        PARTITION BY regions.region_code, b.BrandName
                        ORDER BY bs.BoardSizeId DESC
                    ) AS rn
                FROM regions
                CROSS JOIN dbo.BoardSizes bs
                INNER JOIN dbo.BoardModels bm
                    ON bm.BoardModelId = bs.BoardModelId
                INNER JOIN dbo.Brands b
                    ON b.BrandId = bm.BrandId
                LEFT JOIN dbo.RetailerInventory ri
                    ON ri.BoardSizeId = bs.BoardSizeId
                   AND ri.RegionCode = regions.region_code
                   AND ri.IsActive = 1
                LEFT JOIN dbo.ManufacturerInventory mi
                    ON mi.BoardSizeId = bs.BoardSizeId
                   AND mi.RegionCode = regions.region_code
                   AND COALESCE(mi.IsActive, 1) = 1
                   AND COALESCE(mi.IsAvailable, 0) = 1
                WHERE bm.IsActive = 1
                  AND b.BrandName IN ({brand_names_sql})
                  AND ri.InventoryId IS NULL
                  AND mi.ManufacturerInventoryId IS NULL
            )
            SELECT *
            FROM ranked
            WHERE rn = 1
            """
        )
    )

    cases: list[SearchCase] = []
    for sample_type, rows in (
        ("exact", exact_rows),
        ("close", close_rows),
        ("no_stock", no_stock_rows),
    ):
        for raw_row in rows:
            row = row_to_dict(raw_row)
            board_size_id = row.get("BoardSizeId")
            if board_size_id is None:
                continue
            cases.append(
                SearchCase(
                    region=str(row.get("RegionCode") or ""),
                    board_size_id=int(board_size_id),
                    brand=normalize_brand_name(row.get("BrandName")),
                    model=str(row.get("ModelName") or ""),
                    construction=row.get("Construction"),
                    length=row.get("LengthFeetInches"),
                    label=f"{row.get('RegionCode')} {normalize_brand_name(row.get('BrandName'))} {sample_type} sample",
                )
            )
    deduped: dict[tuple[str, int], SearchCase] = {}
    for case in cases:
        deduped[(case.region, case.board_size_id)] = case
    return list(deduped.values())


def _candidate_counts(region: str, board_size_id: int) -> tuple[int, int]:
    official = backend_app.fetch_one_with_retry(
        text(
            """
            SELECT
                bs.BoardSizeId,
                bs.LengthFeetInches,
                bs.VolumeLitres,
                bs.Construction,
                bm.BoardModelId,
                b.BrandId
            FROM dbo.BoardSizes bs
            INNER JOIN dbo.BoardModels bm
                ON bm.BoardModelId = bs.BoardModelId
            INNER JOIN dbo.Brands b
                ON b.BrandId = bm.BrandId
            WHERE bs.BoardSizeId = :board_size_id
            """
        ),
        {"board_size_id": board_size_id},
    )
    if not official:
        return 0, 0
    target = row_to_dict(official)
    target_length = target.get("LengthFeetInches")
    close_rows = execute_with_retry(
        text(
            f"""
            SELECT
                SUM(
                    CASE
                        WHEN ri.BoardModelId = :board_model_id
                         AND ri.BoardSizeId <> :board_size_id
                         AND ({available_status_sql('ri.StockStatus')})
                         AND ri.IsActive = 1
                         AND ri.RegionCode = :region
                         AND ri.LengthFeetInches IN (:length, :one_down, :one_up)
                        THEN 1 ELSE 0
                    END
                ) AS CloseCandidateCount,
                SUM(
                    CASE
                        WHEN ri.BrandId = :brand_id
                         AND ri.BoardSizeId <> :board_size_id
                         AND ri.ProductUrl IS NOT NULL
                         AND ({available_status_sql('ri.StockStatus')})
                         AND ri.IsActive = 1
                         AND ri.RegionCode = :region
                        THEN 1 ELSE 0
                    END
                ) AS FallbackCandidateCount
            FROM dbo.RetailerInventory ri
            WHERE ri.RegionCode = :region
            """
        ),
        {
            "region": region,
            "board_model_id": target["BoardModelId"],
            "board_size_id": target["BoardSizeId"],
            "brand_id": target["BrandId"],
            "length": target_length,
            "one_down": backend_app.length_to_inches(target_length) and f"{(backend_app.length_to_inches(target_length)-1)//12}'{(backend_app.length_to_inches(target_length)-1)%12}",
            "one_up": backend_app.length_to_inches(target_length) and f"{(backend_app.length_to_inches(target_length)+1)//12}'{(backend_app.length_to_inches(target_length)+1)%12}",
        },
    )
    row = row_to_dict(close_rows[0]) if close_rows else {}
    return int(row.get("FallbackCandidateCount") or 0), int(row.get("CloseCandidateCount") or 0)


def build_search_behaviour_matrix() -> dict[str, Any]:
    seed_cases = _build_seed_cases()
    cases = list(seed_cases)
    sampled_cases = _sample_cases()
    truncated_sampled_cases = sampled_cases[:DEFAULT_MAX_AUTO_CASES]
    for sampled_case in truncated_sampled_cases:
        if all(existing.board_size_id != sampled_case.board_size_id or existing.region != sampled_case.region for existing in cases):
            cases.append(sampled_case)
    results = []
    for case in cases:
        search_payload = backend_app.search_inventory(case.board_size_id, case.region)
        fallback_count, close_count = _candidate_counts(case.region, case.board_size_id)
        if case.brand == "Unknown":
            manufacturer = search_payload.get("manufacturer") or {}
            case = SearchCase(
                region=case.region,
                board_size_id=case.board_size_id,
                brand=str(manufacturer.get("brandName") or "Unknown"),
                model=str(manufacturer.get("modelName") or "Unknown"),
                construction=manufacturer.get("construction"),
                length=manufacturer.get("length"),
                label=case.label,
            )
        results.append(search_case_result(case, search_payload, fallback_count, close_count))
    return {
        "cases": results,
        "summary": {
            "casesRun": len(results),
            "seedCases": len(seed_cases),
            "autoSampleCasesSelected": len(truncated_sampled_cases),
            "autoSampleCasesAvailable": len(sampled_cases),
            "autoSampleCasesTruncated": max(0, len(sampled_cases) - len(truncated_sampled_cases)),
            "fallbackExpectedButMissing": sum(1 for row in results if row["reasonIfMismatch"] == "fallback_expected_but_not_returned"),
            "closeExpectedButMissing": sum(1 for row in results if row["reasonIfMismatch"] == "close_matches_expected_but_not_returned"),
        },
    }
