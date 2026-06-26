from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import text

from audits.common import (
    ALBUM_EXPECTED_MODELS,
    SUPPORTED_BRANDS,
    choose_timestamp_expression,
    format_timestamp,
    load_table_columns,
    normalize_text,
    resolve_supported_brands,
    row_to_dict,
)
from market_intelligence.db import execute_with_retry


def summarize_brand_health(
    brand_entry: dict[str, Any],
    model_rows: list[dict[str, Any]],
    size_rows: list[dict[str, Any]],
    dropdown_models: list[str],
) -> dict[str, Any]:
    size_count_by_model_id = {
        int(row["BoardModelId"]): int(row["SizeCount"] or 0)
        for row in size_rows
    }
    canonical_model_names = [str(row["ModelName"]) for row in model_rows]
    dropdown_names = sorted(dropdown_models)
    canonical_name_set = set(canonical_model_names)
    dropdown_name_set = set(dropdown_names)

    duplicate_normalized_names = sorted(
        normalized_name
        for normalized_name, count in Counter(normalize_text(name) for name in canonical_model_names).items()
        if normalized_name and count > 1
    )
    models_without_sizes = sorted(
        str(row["ModelName"])
        for row in model_rows
        if size_count_by_model_id.get(int(row["BoardModelId"]), 0) == 0
    )
    timestamps = [
        row.get("ModelTimestamp")
        for row in model_rows
        if row.get("ModelTimestamp") is not None
    ]
    suspicious_indicators: list[str] = []
    if not model_rows:
        suspicious_indicators.append("brand_has_zero_active_models")
    if models_without_sizes:
        suspicious_indicators.append(f"models_without_sizes:{len(models_without_sizes)}")
    if duplicate_normalized_names:
        suspicious_indicators.append(f"duplicate_normalized_model_names:{len(duplicate_normalized_names)}")
    if canonical_name_set != dropdown_name_set:
        suspicious_indicators.append("dropdown_model_mismatch")

    payload: dict[str, Any] = {
        "brandName": brand_entry["displayName"],
        "brandId": brand_entry.get("primaryBrandId"),
        "brandIds": brand_entry.get("brandIds", []),
        "canonicalModelCount": len(model_rows),
        "canonicalSizeCount": sum(size_count_by_model_id.values()),
        "modelsWithSizes": sum(
            1
            for row in model_rows
            if size_count_by_model_id.get(int(row["BoardModelId"]), 0) > 0
        ),
        "modelsWithoutSizes": models_without_sizes,
        "constructionsCount": len(
            {
                normalize_text(size_row.get("Construction"))
                for size_row in size_rows
                if normalize_text(size_row.get("Construction"))
            }
        ),
        "minModelTimestamp": format_timestamp(min(timestamps)) if timestamps else None,
        "maxModelTimestamp": format_timestamp(max(timestamps)) if timestamps else None,
        "dropdownModelCount": len(dropdown_names),
        "modelsReturnedByApi": dropdown_names,
        "modelsPresentInSqlButMissingFromApi": sorted(canonical_name_set - dropdown_name_set),
        "modelsWithNoSizes": models_without_sizes,
        "duplicateNormalisedModelNames": duplicate_normalized_names,
        "suspiciousModelLossIndicators": suspicious_indicators,
    }
    if brand_entry["displayName"] == "Album":
        expected = set(ALBUM_EXPECTED_MODELS)
        present = canonical_name_set & expected
        missing = expected - canonical_name_set
        payload["albumExpectedModelsPresent"] = sorted(present)
        payload["albumExpectedModelsMissing"] = sorted(missing)
        if missing:
            payload["suspiciousModelLossIndicators"].append(f"album_expected_models_missing:{len(missing)}")
    return payload


def build_canonical_catalogue_health_report() -> dict[str, Any]:
    board_model_columns = load_table_columns("BoardModels")
    model_timestamp_expr = choose_timestamp_expression("bm", board_model_columns)
    model_timestamp_sql = (
        f"{model_timestamp_expr} AS ModelTimestamp"
        if model_timestamp_expr
        else "CAST(NULL AS datetimeoffset) AS ModelTimestamp"
    )
    brand_entries = resolve_supported_brands()
    if not any(entry["brandIds"] for entry in brand_entries):
        return {
            "brands": [],
            "summary": {
                "supportedBrandCount": len(SUPPORTED_BRANDS),
                "resolvedBrandCount": 0,
                "brandsMissingFromSql": list(SUPPORTED_BRANDS),
            },
        }

    all_brand_ids = [
        brand_id
        for entry in brand_entries
        for brand_id in entry["brandIds"]
    ]
    model_placeholders = ", ".join(f":brand_id_{idx}" for idx in range(len(all_brand_ids)))
    params = {
        f"brand_id_{idx}": brand_id
        for idx, brand_id in enumerate(all_brand_ids)
    }
    model_rows = [
        row_to_dict(row)
        for row in execute_with_retry(
            text(
                f"""
                SELECT
                    bm.BoardModelId,
                    bm.BrandId,
                    bm.ModelName,
                    {model_timestamp_sql}
                FROM dbo.BoardModels bm
                WHERE bm.IsActive = 1
                  AND bm.BrandId IN ({model_placeholders})
                ORDER BY bm.BrandId, bm.ModelName
                """
            ),
            params,
        )
    ]
    size_rows = [
        row_to_dict(row)
        for row in execute_with_retry(
            text(
                f"""
                SELECT
                    bm.BrandId,
                    bs.BoardModelId,
                    COUNT(*) AS SizeCount,
                    COUNT(DISTINCT NULLIF(LTRIM(RTRIM(COALESCE(bs.Construction, ''))), '')) AS ConstructionCount,
                    MIN(NULLIF(LTRIM(RTRIM(COALESCE(bs.Construction, ''))), '')) AS Construction
                FROM dbo.BoardSizes bs
                INNER JOIN dbo.BoardModels bm
                    ON bm.BoardModelId = bs.BoardModelId
                WHERE bm.IsActive = 1
                  AND bm.BrandId IN ({model_placeholders})
                GROUP BY bm.BrandId, bs.BoardModelId
                """
            ),
            params,
        )
    ]
    models_by_brand: dict[int, list[dict[str, Any]]] = defaultdict(list)
    sizes_by_brand: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in model_rows:
        models_by_brand[int(row["BrandId"])].append(row)
    for row in size_rows:
        sizes_by_brand[int(row["BrandId"])].append(row)

    brands = []
    missing_from_sql = []
    for entry in brand_entries:
        display_name = entry["displayName"]
        brand_ids = entry["brandIds"]
        if not brand_ids:
            missing_from_sql.append(display_name)
            brands.append(
                {
                    "brandName": display_name,
                    "brandId": None,
                    "brandIds": [],
                    "canonicalModelCount": 0,
                    "canonicalSizeCount": 0,
                    "modelsWithSizes": 0,
                    "modelsWithoutSizes": [],
                    "constructionsCount": 0,
                    "minModelTimestamp": None,
                    "maxModelTimestamp": None,
                    "dropdownModelCount": 0,
                    "modelsReturnedByApi": [],
                    "modelsPresentInSqlButMissingFromApi": [],
                    "modelsWithNoSizes": [],
                    "duplicateNormalisedModelNames": [],
                    "suspiciousModelLossIndicators": ["brand_missing_from_sql"],
                }
            )
            continue

        entry_models = [
            row
            for brand_id in brand_ids
            for row in models_by_brand.get(brand_id, [])
        ]
        entry_sizes = [
            row
            for brand_id in brand_ids
            for row in sizes_by_brand.get(brand_id, [])
        ]
        dropdown_models = sorted(str(row["ModelName"]) for row in entry_models)
        brands.append(
            summarize_brand_health(
                entry,
                entry_models,
                entry_sizes,
                dropdown_models,
            )
        )

    return {
        "brands": brands,
        "summary": {
            "supportedBrandCount": len(SUPPORTED_BRANDS),
            "resolvedBrandCount": len([entry for entry in brand_entries if entry["brandIds"]]),
            "brandsMissingFromSql": missing_from_sql,
            "brandsWithSuspiciousIndicators": [
                brand["brandName"]
                for brand in brands
                if brand.get("suspiciousModelLossIndicators")
            ],
        },
    }

