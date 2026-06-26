from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from audits.common import (
    BRAND_SOURCE_FILES,
    GLOBAL_ALIAS_CANDIDATES,
    SCRIPT_OUTPUT_ROOT,
    SUPPORTED_BRANDS,
    choose_timestamp_expression,
    format_timestamp,
    load_json_file,
    load_table_columns,
    normalize_text,
    resolve_supported_brands,
    row_to_dict,
)
from market_intelligence.db import execute_with_retry


def _clean_model_name(value: Any) -> str:
    return str(value or "").strip()


def _extract_source_models(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    ignored_models = {"videos"}
    data = load_json_file(path)
    if isinstance(data, list) and data and isinstance(data[0], str):
        return sorted(
            {
                cleaned
                for item in data
                for cleaned in [_clean_model_name(item)]
                if cleaned and normalize_text(cleaned) not in ignored_models
            }
        )
    if isinstance(data, list):
        return sorted(
            {
                cleaned
                for item in data
                for cleaned in [
                    _clean_model_name(item.get("model") or item.get("model_name") or item.get("modelName"))
                ]
                if isinstance(item, dict)
                and cleaned
                and normalize_text(cleaned) not in ignored_models
            }
        )
    return []


def _extract_latest_build_timestamp(report_path: Path | None) -> str | None:
    if report_path is None or not report_path.exists():
        return None
    return datetime.fromtimestamp(report_path.stat().st_mtime, tz=timezone.utc).isoformat()


def _source_report_summary(report_path: Path | None) -> dict[str, Any]:
    if report_path is None or not report_path.exists():
        return {"exists": False}
    try:
        data = load_json_file(report_path)
    except Exception as exc:
        return {"exists": True, "error": type(exc).__name__}
    summary = {"exists": True}
    for key in (
        "rows",
        "models",
        "catalogue_rows",
        "models_with_rows",
        "products_seen",
        "failure_count",
        "failures",
        "missing_models",
        "scraped_model_count",
        "expected_model_count",
        "constructions",
        "output_file",
    ):
        if key in data:
            summary[key] = data[key]
    return summary


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
    source_files = BRAND_SOURCE_FILES.get(brand_entry["displayName"], {})
    source_models = _extract_source_models(source_files.get("expected_models") or source_files.get("catalogue"))
    source_name_set = set(source_models)
    canonical_by_normalized = {normalize_text(name): name for name in canonical_model_names}
    source_by_normalized = {normalize_text(name): name for name in source_models}
    canonical_normalized = set(canonical_by_normalized)
    source_normalized = set(source_by_normalized)
    alias_candidates = GLOBAL_ALIAS_CANDIDATES.get(brand_entry["displayName"], {})
    alias_pairs = {
        normalize_text(source_name): normalize_text(canonical_name)
        for source_name, canonical_name in alias_candidates.items()
    }
    alias_candidate_rows = sorted(
        (
            source_by_normalized[source_key],
            canonical_by_normalized[canonical_key],
        )
        for source_key, canonical_key in alias_pairs.items()
        if source_key in source_normalized and canonical_key in canonical_normalized
    )
    direct_missing = sorted(
        source_by_normalized[source_key]
        for source_key in source_normalized
        if source_key not in canonical_normalized
        and (
            source_key not in alias_pairs
            or alias_pairs[source_key] not in canonical_normalized
        )
    )
    retired_candidates = (
        sorted(canonical_by_normalized[key] for key in canonical_normalized - source_normalized)
        if source_name_set
        else []
    )
    latest_weekly_build = _extract_latest_build_timestamp(source_files.get("report") or source_files.get("catalogue"))
    source_report = _source_report_summary(source_files.get("report"))

    duplicate_normalized_names = sorted(
        normalized_name
        for normalized_name, count in Counter(normalize_text(name) for name in canonical_model_names).items()
        if normalized_name and count > 1
    )
    models_with_description = sum(1 for row in model_rows if str(row.get("Description") or "").strip())
    models_with_official_url = sum(1 for row in model_rows if str(row.get("OfficialProductUrl") or "").strip())
    models_with_official_image = sum(1 for row in model_rows if str(row.get("OfficialImageUrl") or "").strip())
    models_with_board_category = sum(1 for row in model_rows if str(row.get("BoardCategory") or "").strip())
    models_with_wave_range = sum(1 for row in model_rows if str(row.get("RecommendedWaveRange") or "").strip())
    models_with_surfer_weight = sum(1 for row in model_rows if str(row.get("RecommendedSurferWeight") or "").strip())
    models_without_sizes = sorted(
        str(row["ModelName"])
        for row in model_rows
        if size_count_by_model_id.get(int(row["BoardModelId"]), 0) == 0
    )
    models_missing_descriptions = sorted(
        str(row["ModelName"])
        for row in model_rows
        if not str(row.get("Description") or "").strip()
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
    if direct_missing:
        suspicious_indicators.append(f"official_models_missing:{len(direct_missing)}")
    if source_report.get("failure_count"):
        suspicious_indicators.append(f"builder_failures:{source_report['failure_count']}")

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
        "modelsWithDescription": models_with_description,
        "modelsMissingDescriptions": models_missing_descriptions,
        "descriptionCoveragePct": round((models_with_description / len(model_rows)) * 100, 2) if model_rows else None,
        "modelsWithOfficialUrl": models_with_official_url,
        "officialUrlCoveragePct": round((models_with_official_url / len(model_rows)) * 100, 2) if model_rows else None,
        "modelsWithOfficialImage": models_with_official_image,
        "officialImageCoveragePct": round((models_with_official_image / len(model_rows)) * 100, 2) if model_rows else None,
        "modelsWithBoardCategory": models_with_board_category,
        "boardCategoryCoveragePct": round((models_with_board_category / len(model_rows)) * 100, 2) if model_rows else None,
        "modelsWithRecommendedWaveRange": models_with_wave_range,
        "recommendedWaveRangeCoveragePct": round((models_with_wave_range / len(model_rows)) * 100, 2) if model_rows else None,
        "modelsWithRecommendedSurferWeight": models_with_surfer_weight,
        "recommendedSurferWeightCoveragePct": round((models_with_surfer_weight / len(model_rows)) * 100, 2) if model_rows else None,
        "suspiciousModelLossIndicators": suspicious_indicators,
        "officialModelCount": len(source_models),
        "officialModels": source_models,
        "officialModelsMissingFromCanonical": direct_missing,
        "aliasCandidates": [
            {
                "sourceModel": source_name,
                "canonicalModel": canonical_name,
            }
            for source_name, canonical_name in alias_candidate_rows
        ],
        "retiredCanonicalCandidates": retired_candidates,
        "latestWeeklyBuildUtc": latest_weekly_build,
        "sourceCatalogue": source_report,
    }
    return payload


def build_canonical_catalogue_health_report() -> dict[str, Any]:
    board_model_columns = load_table_columns("BoardModels")
    model_timestamp_expr = choose_timestamp_expression("bm", board_model_columns)
    model_timestamp_sql = (
        f"{model_timestamp_expr} AS ModelTimestamp"
        if model_timestamp_expr
        else "CAST(NULL AS datetimeoffset) AS ModelTimestamp"
    )
    description_sql = "bm.Description AS Description" if "Description" in board_model_columns else "CAST(NULL AS nvarchar(max)) AS Description"
    official_product_url_sql = "bm.OfficialProductUrl AS OfficialProductUrl" if "OfficialProductUrl" in board_model_columns else "CAST(NULL AS nvarchar(1000)) AS OfficialProductUrl"
    official_image_url_sql = "bm.OfficialImageUrl AS OfficialImageUrl" if "OfficialImageUrl" in board_model_columns else "CAST(NULL AS nvarchar(1000)) AS OfficialImageUrl"
    board_category_sql = "bm.BoardCategory AS BoardCategory" if "BoardCategory" in board_model_columns else "CAST(NULL AS nvarchar(255)) AS BoardCategory"
    recommended_wave_range_sql = "bm.RecommendedWaveRange AS RecommendedWaveRange" if "RecommendedWaveRange" in board_model_columns else "CAST(NULL AS nvarchar(255)) AS RecommendedWaveRange"
    recommended_surfer_weight_sql = "bm.RecommendedSurferWeight AS RecommendedSurferWeight" if "RecommendedSurferWeight" in board_model_columns else "CAST(NULL AS nvarchar(255)) AS RecommendedSurferWeight"
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
                    {description_sql},
                    {official_product_url_sql},
                    {official_image_url_sql},
                    {board_category_sql},
                    {recommended_wave_range_sql},
                    {recommended_surfer_weight_sql},
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

    schema_support = {
        "description": "Description" in board_model_columns,
        "officialProductUrl": "OfficialProductUrl" in board_model_columns,
        "officialImageUrl": "OfficialImageUrl" in board_model_columns,
        "boardCategory": "BoardCategory" in board_model_columns,
        "recommendedWaveRange": "RecommendedWaveRange" in board_model_columns,
        "recommendedSurferWeight": "RecommendedSurferWeight" in board_model_columns,
        "technologyNotes": False,
        "aliases": False,
        "sizeRange": False,
    }
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
            "brandsMissingDescriptions": [
                {
                    "brandName": brand["brandName"],
                    "modelsMissingDescriptions": len(brand.get("modelsMissingDescriptions", [])),
                    "descriptionCoveragePct": brand.get("descriptionCoveragePct"),
                }
                for brand in brands
                if brand.get("modelsMissingDescriptions")
            ],
            "schemaSupport": schema_support,
            "bodhiReadinessGaps": [
                "Technology/construction notes do not have a dedicated canonical SQL column yet.",
                "Model aliases are maintained in scraper/audit metadata, not a canonical SQL alias table.",
                "Size range is derivable from BoardSizes but is not stored as a dedicated canonical field.",
            ],
            "canonicalAuditOutputFile": str(SCRIPT_OUTPUT_ROOT / "canonical_catalogue_audit.json"),
        },
    }
