from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import text

from market_intelligence.db import engine, execute_with_retry
from scripts.run_supported_inventory_linkage_backfill import compute_supported_linkage_report
from utils.structured_logging import ROOT, utc_timestamp


EXPECTATIONS_PATH = ROOT / "config" / "region_source_expectations.json"
SERVICE_NAME = "operations_dashboard"
DASHBOARD_VERSION = "sprint6_operations_dashboard_v1"
SUPPORTED_BRAND_SET = {
    "Album",
    "Channel Islands",
    "Chemistry Surfboards",
    "Chilli",
    "Christenson",
    "DHD",
    "DMS",
    "Firewire",
    "Haydenshapes",
    "JS Industries",
    "Lost",
    "Misfit",
    "Misfit Shapes",
    "Pukas",
    "Pyzel",
    "Rusty",
    "Sharp Eye",
    "Simon Anderson",
}


def _sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


SUPPORTED_BRANDS_SQL_LIST = ", ".join(
    _sql_quote(brand)
    for brand in sorted(SUPPORTED_BRAND_SET)
)
REGION_ORDER = {
    "AU": 0,
    "EU": 1,
    "ID": 2,
    "US": 3,
}
STATUS_PRIORITY = {
    "red": 3,
    "yellow": 2,
    "green": 1,
    "grey": 0,
}


RETAILER_REGION_QUERY = """
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>') AS RegionCode,
    COUNT(*) AS ActiveRetailerRows,
    SUM(CASE
            WHEN ri.StockStatus IS NULL
                 OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN ('in stock', 'instock', 'in_stock', 'available', 'true')
                THEN 1 ELSE 0
        END) AS AvailableRetailerRows,
    SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRows,
    SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRows,
    COUNT(DISTINCT ri.RetailerId) AS RetailerCount,
    MAX(COALESCE(ri.LastCheckedUtc, ri.UpdatedAtUtc, ri.CreatedAtUtc)) AS LatestRetailerRefreshUtc
FROM dbo.RetailerInventory ri
WHERE ri.IsActive = 1
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>')
"""

MFA_REGION_QUERY = """
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(mi.RegionCode)), ''), '<NULL>') AS RegionCode,
    COUNT(*) AS ActiveMfaRows,
    SUM(CASE WHEN COALESCE(mi.IsAvailable, 0) = 1 THEN 1 ELSE 0 END) AS AvailableMfaRows,
    SUM(CASE WHEN mi.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRows,
    SUM(CASE WHEN mi.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRows,
    COUNT(DISTINCT mi.BrandId) AS BrandCount,
    MAX(COALESCE(mi.ScrapedAtUtc, mi.UpdatedAtUtc, mi.CreatedAtUtc)) AS LatestMfaRefreshUtc
FROM dbo.ManufacturerInventory mi
WHERE COALESCE(mi.IsActive, 1) = 1
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(mi.RegionCode)), ''), '<NULL>')
"""

RETAILER_HEALTH_QUERY = """
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>') AS RegionCode,
    r.RetailerName,
    COUNT(*) AS ActiveRows,
    SUM(CASE
            WHEN ri.StockStatus IS NULL
                 OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN ('in stock', 'instock', 'in_stock', 'available', 'true')
                THEN 1 ELSE 0
        END) AS AvailableRows,
    SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRows,
    SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRows,
    MAX(COALESCE(ri.LastCheckedUtc, ri.UpdatedAtUtc, ri.CreatedAtUtc)) AS LatestRefreshUtc
FROM dbo.RetailerInventory ri
INNER JOIN dbo.Retailers r
    ON r.RetailerId = ri.RetailerId
WHERE ri.IsActive = 1
GROUP BY
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>'),
    r.RetailerName
"""

MFA_HEALTH_QUERY = """
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(mi.RegionCode)), ''), '<NULL>') AS RegionCode,
    b.BrandName,
    COUNT(*) AS ActiveRows,
    SUM(CASE WHEN COALESCE(mi.IsAvailable, 0) = 1 THEN 1 ELSE 0 END) AS AvailableRows,
    SUM(CASE WHEN mi.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRows,
    SUM(CASE WHEN mi.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRows,
    MAX(COALESCE(mi.ScrapedAtUtc, mi.UpdatedAtUtc, mi.CreatedAtUtc)) AS LatestRefreshUtc
FROM dbo.ManufacturerInventory mi
LEFT JOIN dbo.Brands b
    ON b.BrandId = mi.BrandId
WHERE COALESCE(mi.IsActive, 1) = 1
GROUP BY
    COALESCE(NULLIF(LTRIM(RTRIM(mi.RegionCode)), ''), '<NULL>'),
    b.BrandName
"""

SUPPORTED_COUNTS_QUERY = f"""
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>') AS RegionCode,
    SUM(CASE WHEN b.BrandName IN ({SUPPORTED_BRANDS_SQL_LIST}) THEN 1 ELSE 0 END) AS SupportedRows,
    SUM(CASE WHEN b.BrandName NOT IN ({SUPPORTED_BRANDS_SQL_LIST}) OR b.BrandName IS NULL THEN 1 ELSE 0 END) AS UnsupportedRows,
    SUM(CASE
            WHEN b.BrandName IN ({SUPPORTED_BRANDS_SQL_LIST})
             AND LOWER(COALESCE(ri.RawProductTitle, '')) LIKE '%used%'
                THEN 1 ELSE 0
        END) AS UsedSupportedRows
FROM dbo.RetailerInventory ri
LEFT JOIN dbo.Brands b
    ON b.BrandId = ri.BrandId
WHERE ri.IsActive = 1
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>')
"""

SUPPORTED_MODELS_QUERY = f"""
SELECT
    bm.BoardModelId,
    b.BrandName,
    bm.ModelName
FROM dbo.BoardModels bm
INNER JOIN dbo.Brands b
    ON b.BrandId = bm.BrandId
WHERE bm.IsActive = 1
  AND b.BrandName IN ({SUPPORTED_BRANDS_SQL_LIST})
"""

ACTIVE_RETAILER_MODELS_QUERY = """
SELECT DISTINCT
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>') AS RegionCode,
    ri.BoardModelId
FROM dbo.RetailerInventory ri
WHERE ri.IsActive = 1
  AND ri.BoardModelId IS NOT NULL
"""

ACTIVE_MFA_MODELS_QUERY = """
SELECT DISTINCT
    COALESCE(NULLIF(LTRIM(RTRIM(mi.RegionCode)), ''), '<NULL>') AS RegionCode,
    mi.BoardModelId
FROM dbo.ManufacturerInventory mi
WHERE COALESCE(mi.IsActive, 1) = 1
  AND mi.BoardModelId IS NOT NULL
"""


@dataclass(frozen=True)
class StatusResult:
    color: str
    label: str
    reason: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text_value = str(value).strip()
    if not text_value:
        return None
    text_value = text_value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text_value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_source_expectations(path: Path | None = None) -> dict[str, Any]:
    return _json_load(path or EXPECTATIONS_PATH)


def pct(numerator: int, denominator: int) -> float:
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _sort_region(region: str) -> tuple[int, str]:
    clean = str(region or "").upper()
    return (REGION_ORDER.get(clean, 99), clean)


def region_sort_key(region_payload: dict[str, Any]) -> tuple[int, str]:
    return _sort_region(str(region_payload.get("region") or region_payload.get("regionCode") or ""))


def classify_source_status(
    applicability: str,
    latest_refresh_utc: Any,
    active_rows: int,
    *,
    green_hours: int = 24,
    yellow_hours: int = 48,
    now: datetime | None = None,
) -> StatusResult:
    current_time = now or _utcnow()
    normalized = str(applicability or "expected").strip().lower()
    if normalized in {"not_applicable", "dealer_network_only"}:
        label = "dealer_network_only" if normalized == "dealer_network_only" else "not_applicable"
        reason = "Direct manufacturer stock is intentionally not tracked for this region." if normalized == "dealer_network_only" else "This source is not applicable in this region."
        return StatusResult("grey", label, reason)
    if normalized in {"planned", "partial"}:
        if active_rows > 0 and latest_refresh_utc:
            return StatusResult("yellow", "partial", "Source has rows but remains marked as partial or not fully onboarded.")
        return StatusResult("yellow", "planned", "Source is planned or partially onboarded in this region.")

    latest_refresh = _parse_timestamp(latest_refresh_utc)
    if latest_refresh is None:
        return StatusResult("red", "missing", "Expected source has no successful refresh timestamp.")
    if active_rows <= 0:
        return StatusResult("red", "zero_rows", "Expected source has zero active rows.")

    age = current_time - latest_refresh
    if age <= timedelta(hours=green_hours):
        return StatusResult("green", "healthy", f"Fresh within {green_hours} hours.")
    if age <= timedelta(hours=yellow_hours):
        return StatusResult("yellow", "stale", f"Stale between {green_hours} and {yellow_hours} hours.")
    return StatusResult("red", "stale", f"Stale beyond {yellow_hours} hours.")


def classify_search_health(
    supported_model_link_pct: float | None,
    canonical_size_family_link_pct: float | None,
    exact_board_size_link_pct: float | None,
) -> StatusResult:
    if supported_model_link_pct is None or canonical_size_family_link_pct is None or exact_board_size_link_pct is None:
        return StatusResult("yellow", "partial", "Search telemetry is incomplete; using current linkage metrics only.")
    if supported_model_link_pct >= 75 and canonical_size_family_link_pct >= 45 and exact_board_size_link_pct >= 25:
        return StatusResult("green", "healthy", "Regional linkage quality is within current operating thresholds.")
    if supported_model_link_pct >= 60 and canonical_size_family_link_pct >= 30 and exact_board_size_link_pct >= 15:
        return StatusResult("yellow", "degraded", "Regional linkage quality is usable but below preferred targets.")
    return StatusResult("red", "degraded", "Regional linkage quality is below safe operating thresholds.")


def combine_status_colors(*colors: str) -> str:
    selected = "grey"
    selected_priority = -1
    for color in colors:
        priority = STATUS_PRIORITY.get(color, -1)
        if priority > selected_priority:
            selected = color
            selected_priority = priority
    return selected


def _rows(query: str, params: dict[str, Any] | None = None) -> list[Any]:
    return execute_with_retry(text(query), params or {})


def _row_field(row: Any, field: str, default: Any = None) -> Any:
    if hasattr(row, field):
        value = getattr(row, field)
        return default if value is None else value
    if isinstance(row, dict):
        value = row.get(field, default)
        return default if value is None else value
    return default


def _map_region_rows(rows: list[Any], region_field: str = "RegionCode") -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        region = str(_row_field(row, region_field, "<NULL>")).upper()
        mapped[region] = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    return mapped


def _build_mfa_matrix(
    regions: list[str],
    expectations: dict[str, Any],
    mfa_rows: list[Any],
    linkage_report: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    report_breakdown = {
        (item["regionCode"], item["name"]): item
        for item in linkage_report.get("manufacturerBreakdown", [])
    }
    health_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    known_brands: set[str] = set(expectations.get("mfaBrands", {}).keys())
    for row in mfa_rows:
        region = str(_row_field(row, "RegionCode", "<NULL>")).upper()
        brand = str(_row_field(row, "BrandName", "<unknown>"))
        health_lookup[(region, brand)] = {
            "activeRows": int(_row_field(row, "ActiveRows", 0)),
            "availableRows": int(_row_field(row, "AvailableRows", 0)),
            "linkedModelRows": int(_row_field(row, "LinkedModelRows", 0)),
            "linkedSizeRows": int(_row_field(row, "LinkedSizeRows", 0)),
            "latestRefreshUtc": _row_field(row, "LatestRefreshUtc"),
        }
        known_brands.add(brand)

    matrix = []
    for brand in sorted(name for name in known_brands if name and name != "<unknown>"):
        by_region = {}
        for region in regions:
            applicability = expectations.get("mfaBrands", {}).get(brand, {}).get(region, "not_applicable")
            metrics = health_lookup.get((region, brand), {})
            breakdown = report_breakdown.get((region, brand), {})
            status = classify_source_status(
                applicability,
                metrics.get("latestRefreshUtc"),
                int(metrics.get("activeRows", 0)),
                now=now,
            )
            by_region[region] = {
                "applicability": applicability,
                "statusColor": status.color,
                "statusLabel": status.label,
                "reason": status.reason,
                "lastSuccessfulUpdateUtc": _iso(metrics.get("latestRefreshUtc")),
                "activeRowCount": int(metrics.get("activeRows", 0)),
                "availableBoardCount": int(metrics.get("availableRows", 0)),
                "linkedModelCount": int(metrics.get("linkedModelRows", 0)),
                "linkedSizeCount": int(metrics.get("linkedSizeRows", 0)),
                "supportedModelLinkPct": breakdown.get("linkedModelPctAfter"),
                "exactBoardSizeLinkPct": breakdown.get("linkedSizePctAfter"),
                "canonicalSizeFamilyLinkPct": breakdown.get("linkedSizeFamilyPctAfter"),
            }
        matrix.append({"brand": brand, "regions": by_region})
    return matrix


def _build_retailer_matrix(
    regions: list[str],
    expectations: dict[str, Any],
    retailer_rows: list[Any],
    linkage_report: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    report_breakdown = {
        (item["regionCode"], item["name"]): item
        for item in linkage_report.get("retailerBreakdown", [])
    }
    health_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    known_retailers: set[str] = set(expectations.get("retailers", {}).keys())
    for row in retailer_rows:
        region = str(_row_field(row, "RegionCode", "<NULL>")).upper()
        retailer_name = str(_row_field(row, "RetailerName", "<unknown>"))
        health_lookup[(region, retailer_name)] = {
            "activeRows": int(_row_field(row, "ActiveRows", 0)),
            "availableRows": int(_row_field(row, "AvailableRows", 0)),
            "linkedModelRows": int(_row_field(row, "LinkedModelRows", 0)),
            "linkedSizeRows": int(_row_field(row, "LinkedSizeRows", 0)),
            "latestRefreshUtc": _row_field(row, "LatestRefreshUtc"),
        }
        known_retailers.add(retailer_name)

    matrix = []
    for retailer_name in sorted(name for name in known_retailers if name and name != "<unknown>"):
        by_region = {}
        for region in regions:
            metrics = health_lookup.get((region, retailer_name), {})
            fallback_applicability = "expected" if int(metrics.get("activeRows", 0)) > 0 else "not_applicable"
            applicability = expectations.get("retailers", {}).get(retailer_name, {}).get(region, fallback_applicability)
            breakdown = report_breakdown.get((region, retailer_name), {})
            status = classify_source_status(
                applicability,
                metrics.get("latestRefreshUtc"),
                int(metrics.get("activeRows", 0)),
                now=now,
            )
            by_region[region] = {
                "applicability": applicability,
                "statusColor": status.color,
                "statusLabel": status.label,
                "reason": status.reason,
                "lastSuccessfulUpdateUtc": _iso(metrics.get("latestRefreshUtc")),
                "activeRowCount": int(metrics.get("activeRows", 0)),
                "availableBoardCount": int(metrics.get("availableRows", 0)),
                "linkedModelPct": breakdown.get("linkedModelPctAfter"),
                "canonicalSizeFamilyPct": breakdown.get("linkedSizeFamilyPctAfter"),
                "exactBoardSizePct": breakdown.get("linkedSizePctAfter"),
                "rejectedRows": None,
            }
        matrix.append({"retailer": retailer_name, "regions": by_region})
    return matrix


def _iso(value: Any) -> str | None:
    parsed = _parse_timestamp(value)
    if not parsed:
        return None
    return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _region_linkage_lookup(linkage_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["regionCode"]: item
        for item in linkage_report.get("regionBreakdown", [])
    }


def _build_region_overview(
    regions: list[str],
    expectations: dict[str, Any],
    retailer_region_rows: dict[str, dict[str, Any]],
    mfa_region_rows: dict[str, dict[str, Any]],
    linkage_report: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    region_linkage = _region_linkage_lookup(linkage_report)
    overview = []
    for region in regions:
        retailer = retailer_region_rows.get(region, {})
        manufacturer = mfa_region_rows.get(region, {})
        retailer_status = classify_source_status(
            "expected",
            retailer.get("LatestRetailerRefreshUtc"),
            int(retailer.get("ActiveRetailerRows", 0)),
            now=now,
        )
        mfa_status = classify_source_status(
            "expected",
            manufacturer.get("LatestMfaRefreshUtc"),
            int(manufacturer.get("ActiveMfaRows", 0)),
            now=now,
        )
        linkage = region_linkage.get(region, {})
        search_status = classify_search_health(
            linkage.get("linkedModelPctAfter"),
            linkage.get("linkedSizeFamilyPctAfter"),
            linkage.get("linkedSizePctAfter"),
        )
        region_color = combine_status_colors(retailer_status.color, mfa_status.color, search_status.color)
        overview.append(
            {
                "region": region,
                "displayName": expectations.get("regions", {}).get(region, {}).get("displayName", region),
                "statusColor": region_color,
                "regionStatus": region_color,
                "lastRetailerInventoryRefreshUtc": _iso(retailer.get("LatestRetailerRefreshUtc")),
                "lastMfaRefreshUtc": _iso(manufacturer.get("LatestMfaRefreshUtc")),
                "activeRetailerBoardCount": int(retailer.get("ActiveRetailerRows", 0)),
                "activeMfaBoardCount": int(manufacturer.get("ActiveMfaRows", 0)),
                "supportedModelLinkagePct": linkage.get("linkedModelPctAfter"),
                "canonicalSizeFamilyLinkagePct": linkage.get("linkedSizeFamilyPctAfter"),
                "exactBoardSizeLinkagePct": linkage.get("linkedSizePctAfter"),
                "searchHealthStatus": search_status.color,
                "searchHealthReason": search_status.reason,
                "retailerStatus": retailer_status.color,
                "retailerReason": retailer_status.reason,
                "mfaStatus": mfa_status.color,
                "mfaReason": mfa_status.reason,
            }
        )
    return sorted(overview, key=region_sort_key)


def _build_inventory_counts(
    regions: list[str],
    retailer_region_rows: dict[str, dict[str, Any]],
    mfa_region_rows: dict[str, dict[str, Any]],
    supported_counts: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for region in regions:
        retailer = retailer_region_rows.get(region, {})
        manufacturer = mfa_region_rows.get(region, {})
        support = supported_counts.get(region, {})
        supported_rows = int(support.get("SupportedRows", 0))
        used_supported_rows = int(support.get("UsedSupportedRows", 0))
        rows.append(
            {
                "region": region,
                "activeManufacturerInventoryRows": int(manufacturer.get("ActiveMfaRows", 0)),
                "activeRetailerInventoryRows": int(retailer.get("ActiveRetailerRows", 0)),
                "availableMfaBoards": int(manufacturer.get("AvailableMfaRows", 0)),
                "availableRetailerBoards": int(retailer.get("AvailableRetailerRows", 0)),
                "totalActiveBoards": int(manufacturer.get("ActiveMfaRows", 0)) + int(retailer.get("ActiveRetailerRows", 0)),
                "supportedManufacturerRows": supported_rows,
                "unsupportedIgnoredRows": int(support.get("UnsupportedRows", 0)),
                "usedSupportedBoards": used_supported_rows,
                "newSupportedBoards": max(0, supported_rows - used_supported_rows),
            }
        )
    return sorted(rows, key=region_sort_key)


def _build_search_quality(
    regions: list[str],
    linkage_report: dict[str, Any],
) -> list[dict[str, Any]]:
    region_linkage = _region_linkage_lookup(linkage_report)
    rows = []
    for region in regions:
        linkage = region_linkage.get(region, {})
        rows.append(
            {
                "region": region,
                "supportedModelLinkagePct": linkage.get("linkedModelPctAfter"),
                "canonicalSizeFamilyLinkagePct": linkage.get("linkedSizeFamilyPctAfter"),
                "exactBoardSizeLinkagePct": linkage.get("linkedSizePctAfter"),
                "searchTelemetryAvailable": False,
                "exactMatchAvailabilityRate": None,
                "closeMatchAvailabilityRate": None,
                "thinFallbackActivationCount": None,
                "searchesReturningNoResults": None,
                "averageSearchLatencyMs": None,
                "p95SearchLatencyMs": None,
                "searchErrors": None,
                "searchTimeouts": None,
                "search503s": None,
                "notes": "Latency/error search telemetry should be surfaced through Log Analytics workbook queries. SQL builder currently reports linkage quality only.",
            }
        )
    return sorted(rows, key=region_sort_key)


def _build_coverage_gaps(
    regions: list[str],
    supported_models: list[dict[str, Any]],
    retailer_models_by_region: dict[str, set[int]],
    mfa_models_by_region: dict[str, set[int]],
    retailer_matrix: list[dict[str, Any]],
    mfa_matrix: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    supported_by_region: dict[str, dict[str, Any]] = {}
    for region in regions:
        retailer_models = retailer_models_by_region.get(region, set())
        mfa_models = mfa_models_by_region.get(region, set())
        no_retailer = []
        no_mfa = []
        no_stock = []
        only_mfa = []
        only_retailer = []
        brands_low_coverage: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "stocked": 0})
        for model in supported_models:
            board_model_id = int(model["boardModelId"])
            brand_name = str(model["brandName"])
            stocked_retailer = board_model_id in retailer_models
            stocked_mfa = board_model_id in mfa_models
            brands_low_coverage[brand_name]["total"] += 1
            if stocked_retailer or stocked_mfa:
                brands_low_coverage[brand_name]["stocked"] += 1
            model_label = f"{brand_name} {model['modelName']}"
            if not stocked_retailer:
                no_retailer.append(model_label)
            if not stocked_mfa:
                no_mfa.append(model_label)
            if not stocked_retailer and not stocked_mfa:
                no_stock.append(model_label)
            if stocked_mfa and not stocked_retailer:
                only_mfa.append(model_label)
            if stocked_retailer and not stocked_mfa:
                only_retailer.append(model_label)

        low_retailers = []
        for row in retailer_matrix:
            region_cell = row["regions"].get(region, {})
            pct_value = region_cell.get("linkedModelPct")
            if region_cell.get("statusColor") != "grey" and pct_value is not None and pct_value < 60:
                low_retailers.append(
                    {
                        "retailer": row["retailer"],
                        "linkedModelPct": pct_value,
                        "canonicalSizeFamilyPct": region_cell.get("canonicalSizeFamilyPct"),
                        "exactBoardSizePct": region_cell.get("exactBoardSizePct"),
                    }
                )

        low_manufacturers = []
        for row in mfa_matrix:
            region_cell = row["regions"].get(region, {})
            pct_value = region_cell.get("supportedModelLinkPct")
            if region_cell.get("statusColor") != "grey" and pct_value is not None and pct_value < 60:
                low_manufacturers.append(
                    {
                        "brand": row["brand"],
                        "linkedModelPct": pct_value,
                        "canonicalSizeFamilyPct": region_cell.get("canonicalSizeFamilyLinkPct"),
                        "exactBoardSizePct": region_cell.get("exactBoardSizeLinkPct"),
                    }
                )

        supported_by_region[region] = {
            "region": region,
            "supportedCanonicalModelsNoActiveRetailerStock": {
                "count": len(no_retailer),
                "sample": no_retailer[:20],
            },
            "supportedCanonicalModelsNoActiveMfaStock": {
                "count": len(no_mfa),
                "sample": no_mfa[:20],
            },
            "supportedCanonicalModelsNoStockAnywhere": {
                "count": len(no_stock),
                "sample": no_stock[:20],
            },
            "modelsAvailableOnlyViaMfa": {
                "count": len(only_mfa),
                "sample": only_mfa[:20],
            },
            "modelsAvailableOnlyViaRetailers": {
                "count": len(only_retailer),
                "sample": only_retailer[:20],
            },
            "brandsWithLowStockCoverage": [
                {
                    "brand": brand,
                    "stockCoveragePct": pct(counts["stocked"], counts["total"]),
                    "supportedModelCount": counts["total"],
                }
                for brand, counts in sorted(brands_low_coverage.items())
                if pct(counts["stocked"], counts["total"]) < 25
            ][:20],
            "retailersWithLowLinkageQuality": sorted(low_retailers, key=lambda item: (item["linkedModelPct"], item["retailer"]))[:20],
            "manufacturersWithLowLinkageQuality": sorted(low_manufacturers, key=lambda item: (item["linkedModelPct"], item["brand"]))[:20],
        }
    return sorted(supported_by_region.values(), key=region_sort_key)


def _build_alert_summary(
    region_overview: list[dict[str, Any]],
    retailer_matrix: list[dict[str, Any]],
    mfa_matrix: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for region in region_overview:
        if region["retailerStatus"] in {"yellow", "red"}:
            alerts.append(
                {
                    "category": "retailer_inventory",
                    "severity": region["retailerStatus"],
                    "region": region["region"],
                    "message": region["retailerReason"],
                }
            )
        if region["mfaStatus"] in {"yellow", "red"}:
            alerts.append(
                {
                    "category": "manufacturer_availability",
                    "severity": region["mfaStatus"],
                    "region": region["region"],
                    "message": region["mfaReason"],
                }
            )
        if region["searchHealthStatus"] in {"yellow", "red"}:
            alerts.append(
                {
                    "category": "search_quality",
                    "severity": region["searchHealthStatus"],
                    "region": region["region"],
                    "message": region["searchHealthReason"],
                }
            )

    for retailer in retailer_matrix:
        for region, cell in retailer["regions"].items():
            if cell["statusColor"] == "red":
                alerts.append(
                    {
                        "category": "retailer_source",
                        "severity": "red",
                        "region": region,
                        "source": retailer["retailer"],
                        "message": cell["reason"],
                    }
                )
    for brand in mfa_matrix:
        for region, cell in brand["regions"].items():
            if cell["statusColor"] == "red":
                alerts.append(
                    {
                        "category": "mfa_source",
                        "severity": "red",
                        "region": region,
                        "source": brand["brand"],
                        "message": cell["reason"],
                    }
                )
    return alerts


def build_operations_dashboard_metrics(
    *,
    generated_at_utc: str | None = None,
    now: datetime | None = None,
    expectations_path: Path | None = None,
    linkage_report_builder: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    expectations = load_source_expectations(expectations_path)
    generated_at_utc = generated_at_utc or utc_timestamp()
    now = now or _utcnow()
    linkage_report_builder = linkage_report_builder or compute_supported_linkage_report

    retailer_region_rows = _map_region_rows(_rows(RETAILER_REGION_QUERY))
    mfa_region_rows = _map_region_rows(_rows(MFA_REGION_QUERY))
    retailer_health_rows = _rows(RETAILER_HEALTH_QUERY)
    mfa_health_rows = _rows(MFA_HEALTH_QUERY)
    supported_counts_rows = _rows(SUPPORTED_COUNTS_QUERY)
    supported_counts = _map_region_rows(supported_counts_rows)
    supported_models_rows = _rows(SUPPORTED_MODELS_QUERY)
    active_retailer_models_rows = _rows(ACTIVE_RETAILER_MODELS_QUERY)
    active_mfa_models_rows = _rows(ACTIVE_MFA_MODELS_QUERY)

    regions = sorted(
        {
            *expectations.get("regions", {}).keys(),
            *retailer_region_rows.keys(),
            *mfa_region_rows.keys(),
            *[str(_row_field(row, "RegionCode", "<NULL>")).upper() for row in retailer_health_rows],
            *[str(_row_field(row, "RegionCode", "<NULL>")).upper() for row in mfa_health_rows],
        },
        key=_sort_region,
    )
    retailer_models_by_region: defaultdict[str, set[int]] = defaultdict(set)
    for row in active_retailer_models_rows:
        region = str(_row_field(row, "RegionCode", "<NULL>")).upper()
        retailer_models_by_region[region].add(int(_row_field(row, "BoardModelId", 0)))
    mfa_models_by_region: defaultdict[str, set[int]] = defaultdict(set)
    for row in active_mfa_models_rows:
        region = str(_row_field(row, "RegionCode", "<NULL>")).upper()
        mfa_models_by_region[region].add(int(_row_field(row, "BoardModelId", 0)))

    with engine.begin() as conn:
        linkage_report = linkage_report_builder(conn)

    supported_models = [
        {
            "boardModelId": int(_row_field(row, "BoardModelId", 0)),
            "brandName": str(_row_field(row, "BrandName", "")),
            "modelName": str(_row_field(row, "ModelName", "")),
        }
        for row in supported_models_rows
    ]

    retailer_matrix = _build_retailer_matrix(regions, expectations, retailer_health_rows, linkage_report, now)
    mfa_matrix = _build_mfa_matrix(regions, expectations, mfa_health_rows, linkage_report, now)
    region_overview = _build_region_overview(regions, expectations, retailer_region_rows, mfa_region_rows, linkage_report, now)
    inventory_counts = _build_inventory_counts(regions, retailer_region_rows, mfa_region_rows, supported_counts)
    search_quality = _build_search_quality(regions, linkage_report)
    coverage_gaps = _build_coverage_gaps(regions, supported_models, retailer_models_by_region, mfa_models_by_region, retailer_matrix, mfa_matrix)
    alert_summary = _build_alert_summary(region_overview, retailer_matrix, mfa_matrix)

    return {
        "generatedAtUtc": generated_at_utc,
        "service": SERVICE_NAME,
        "version": DASHBOARD_VERSION,
        "regions": regions,
        "regionOverview": region_overview,
        "mfaHealth": mfa_matrix,
        "retailerHealth": retailer_matrix,
        "inventoryCounts": inventory_counts,
        "searchQuality": search_quality,
        "coverageGaps": coverage_gaps,
        "alerts": alert_summary,
        "alertSummary": alert_summary,
        "sourceExpectations": expectations,
        "linkQuality": linkage_report,
    }
