from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import text

from audits.canonical_catalogue_health import build_canonical_catalogue_health_report
from market_intelligence.db import engine, execute_with_retry
from scripts import run_supported_inventory_linkage_backfill as supported_linkage_backfill
from utils.structured_logging import ROOT, STATE_DIR, utc_timestamp


EXPECTATIONS_PATH = ROOT / "config" / "region_source_expectations.json"
JOB_EXPECTATIONS_PATH = ROOT / "config" / "azure_container_jobs.json"
SERVICE_NAME = "operations_dashboard"
DASHBOARD_VERSION = "sprint7_final_closeout_v1"
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
SEVERITY_PRIORITY = {
    "critical": 3,
    "warning": 2,
    "info": 1,
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

SUPPORTED_MODEL_TOTAL_QUERY = f"""
SELECT COUNT(*) AS SupportedModelCount
FROM dbo.BoardModels bm
INNER JOIN dbo.Brands b
    ON b.BrandId = bm.BrandId
WHERE bm.IsActive = 1
  AND b.BrandName IN ({SUPPORTED_BRANDS_SQL_LIST})
"""

SUPPORTED_COVERAGE_GAPS_QUERY = "-- coverage gaps now derive from supported linkage truth"

SUPPORTED_MFA_MODEL_IDS_QUERY = f"""
SELECT DISTINCT
    COALESCE(NULLIF(LTRIM(RTRIM(mi.RegionCode)), ''), '<NULL>') AS RegionCode,
    mi.BoardModelId
FROM dbo.ManufacturerInventory mi
INNER JOIN dbo.BoardModels bm
    ON bm.BoardModelId = mi.BoardModelId
INNER JOIN dbo.Brands b
    ON b.BrandId = bm.BrandId
WHERE COALESCE(mi.IsActive, 1) = 1
  AND mi.BoardModelId IS NOT NULL
  AND b.BrandName IN ({SUPPORTED_BRANDS_SQL_LIST})
"""

SUPPORTED_RETAILER_LINKAGE_REGION_QUERY = f"""
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>') AS RegionCode,
    COUNT(*) AS SupportedRows,
    SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRowsAfter,
    SUM(CASE
            WHEN ri.BoardModelId IS NOT NULL
             AND NULLIF(LTRIM(RTRIM(COALESCE(ri.Construction, ''))), '') IS NOT NULL
             AND NULLIF(LTRIM(RTRIM(COALESCE(ri.LengthFeetInches, ''))), '') IS NOT NULL
                THEN 1 ELSE 0
        END) AS LinkedSizeFamilyRowsAfter,
    SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRowsAfter
FROM dbo.RetailerInventory ri
LEFT JOIN dbo.Brands b
    ON b.BrandId = ri.BrandId
WHERE ri.IsActive = 1
  AND b.BrandName IN ({SUPPORTED_BRANDS_SQL_LIST})
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>')
"""

SUPPORTED_RETAILER_LINKAGE_RETAILER_QUERY = f"""
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>') AS RegionCode,
    r.RetailerName AS Name,
    COUNT(*) AS SupportedRows,
    SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRowsAfter,
    SUM(CASE
            WHEN ri.BoardModelId IS NOT NULL
             AND NULLIF(LTRIM(RTRIM(COALESCE(ri.Construction, ''))), '') IS NOT NULL
             AND NULLIF(LTRIM(RTRIM(COALESCE(ri.LengthFeetInches, ''))), '') IS NOT NULL
                THEN 1 ELSE 0
        END) AS LinkedSizeFamilyRowsAfter,
    SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRowsAfter
FROM dbo.RetailerInventory ri
INNER JOIN dbo.Retailers r
    ON r.RetailerId = ri.RetailerId
LEFT JOIN dbo.Brands b
    ON b.BrandId = ri.BrandId
WHERE ri.IsActive = 1
  AND b.BrandName IN ({SUPPORTED_BRANDS_SQL_LIST})
GROUP BY
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>'),
    r.RetailerName
"""

SUPPORTED_MFA_LINKAGE_BRAND_QUERY = f"""
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(mi.RegionCode)), ''), '<NULL>') AS RegionCode,
    b.BrandName AS Name,
    COUNT(*) AS SupportedRows,
    SUM(CASE WHEN mi.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRowsAfter,
    SUM(CASE
            WHEN mi.BoardModelId IS NOT NULL
             AND NULLIF(LTRIM(RTRIM(COALESCE(mi.Construction, ''))), '') IS NOT NULL
             AND NULLIF(LTRIM(RTRIM(COALESCE(mi.LengthFeetInches, ''))), '') IS NOT NULL
                THEN 1 ELSE 0
        END) AS LinkedSizeFamilyRowsAfter,
    SUM(CASE WHEN mi.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRowsAfter
FROM dbo.ManufacturerInventory mi
LEFT JOIN dbo.Brands b
    ON b.BrandId = mi.BrandId
WHERE COALESCE(mi.IsActive, 1) = 1
  AND b.BrandName IN ({SUPPORTED_BRANDS_SQL_LIST})
GROUP BY
    COALESCE(NULLIF(LTRIM(RTRIM(mi.RegionCode)), ''), '<NULL>'),
    b.BrandName
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


def load_job_expectations(path: Path | None = None) -> dict[str, Any]:
    return _json_load(path or JOB_EXPECTATIONS_PATH)


def _job_entry_script_path(entry_script: str | None) -> Path | None:
    command = str(entry_script or "").strip()
    if not command:
        return None
    parts = command.split()
    if len(parts) < 2:
        return None
    return ROOT / parts[1]


def _job_contract_status(definition: dict[str, Any]) -> StatusResult:
    job_type = str(definition.get("jobType") or "").strip().lower()
    entry_script = _job_entry_script_path(definition.get("entryScript"))
    if entry_script is None:
        return StatusResult("red", "missing_entry_script", "Job contract is missing an entry script.")
    if not entry_script.exists():
        return StatusResult("red", "missing_entry_script", f"Configured entry script is missing: {entry_script.relative_to(ROOT)}")

    writes_tables = {str(name) for name in definition.get("writesTables", [])}
    structured_event = str(definition.get("structuredLogEventName") or "").strip()
    source_text = entry_script.read_text(encoding="utf-8")

    if job_type == "catalogue":
        if "run_au_manufacturer_availability_pipeline.py" in source_text:
            return StatusResult("red", "contract_violation", "Global canonical runner still invokes manufacturer availability.")
        if {"RetailerInventory", "ManufacturerInventory"} & writes_tables:
            return StatusResult("red", "contract_violation", "Global canonical jobs must not write stock tables.")
    elif job_type == "manufacturer_availability":
        if any(table in writes_tables for table in ("BoardModels", "BoardSizes", "RetailerInventory")):
            return StatusResult("red", "contract_violation", "Manufacturer availability jobs must not write canonical or retailer inventory tables.")
        normalized_source = source_text.lower()
        if "planning only" in normalized_source or "must not write sql" in normalized_source or "intentionally disabled" in normalized_source:
            return StatusResult("red", "planning_only", "Configured manufacturer availability runner is still a planning scaffold, not a live SQL writer.")
    elif job_type == "retailer_inventory":
        if any(table in writes_tables for table in ("BoardModels", "BoardSizes", "ManufacturerInventory")):
            return StatusResult("red", "contract_violation", "Retailer inventory jobs must not write canonical or manufacturer inventory tables.")
    elif job_type == "market_intelligence":
        if {"BoardModels", "BoardSizes", "ManufacturerInventory"} & writes_tables:
            return StatusResult("red", "contract_violation", "Market intelligence jobs must not mutate canonical or manufacturer inventory tables.")

    if not structured_event:
        return StatusResult("yellow", "missing_structured_log", "Structured log event name is not configured for this job.")
    return StatusResult("green", "healthy", "Configured job contract matches the Gen 3 layer definition.")


def _load_job_state(job_name: str) -> dict[str, Any] | None:
    path = STATE_DIR / f"{job_name}.json"
    if not path.exists():
        return None
    try:
        return _json_load(path)
    except Exception:
        return None


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
    if supported_model_link_pct is None or canonical_size_family_link_pct is None:
        return StatusResult("yellow", "partial", "Search quality metrics are incomplete; linkage truth is not yet available for this region.")
    if supported_model_link_pct >= 85 and canonical_size_family_link_pct >= 60:
        return StatusResult("green", "healthy", "Model and size-family linkage are within preferred operating thresholds.")
    if supported_model_link_pct >= 75 and canonical_size_family_link_pct >= 40:
        return StatusResult("yellow", "degraded", "Model and size-family linkage are usable but below preferred targets.")
    return StatusResult("red", "degraded", "Model or size-family linkage is below the safe operating threshold.")


def combine_status_colors(*colors: str) -> str:
    selected = "grey"
    selected_priority = -1
    for color in colors:
        priority = STATUS_PRIORITY.get(color, -1)
        if priority > selected_priority:
            selected = color
            selected_priority = priority
    return selected


def _average_pct(values: list[float | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 2)


def _safe_pct(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _status_sort_value(color: str) -> tuple[int, int]:
    normalized = str(color or "grey").lower()
    return (-STATUS_PRIORITY.get(normalized, -1), 0)


def _alert_severity_from_status(color: str) -> str:
    normalized = str(color or "").lower()
    if normalized == "red":
        return "critical"
    if normalized == "yellow":
        return "warning"
    return "info"


def _job_row_metric(
    metric_source: str,
    region: str,
    retailer_region_rows: dict[str, dict[str, Any]],
    mfa_region_rows: dict[str, dict[str, Any]],
    catalogue_metrics: dict[str, Any],
) -> tuple[datetime | None, int | None, str]:
    normalized_source = str(metric_source or "").strip().lower()
    if normalized_source == "retailer_inventory":
        row = retailer_region_rows.get(region, {})
        return (
            _parse_timestamp(row.get("LatestRetailerRefreshUtc")),
            int(row.get("ActiveRetailerRows") or 0),
            "sql_freshness",
        )
    if normalized_source == "manufacturer_inventory":
        row = mfa_region_rows.get(region, {})
        return (
            _parse_timestamp(row.get("LatestMfaRefreshUtc")),
            int(row.get("ActiveMfaRows") or 0),
            "sql_freshness",
        )
    if normalized_source == "catalogue":
        return (
            _parse_timestamp(catalogue_metrics.get("latestSuccessUtc")),
            int(catalogue_metrics.get("modelCount") or 0),
            "sql_catalogue_freshness",
        )
    return (None, None, "job_state")


def _job_rows_from_state(state: dict[str, Any] | None) -> tuple[int | None, int | None]:
    if not state:
        return (None, None)
    rows_inserted = state.get("rows_inserted")
    if rows_inserted is None:
        rows_inserted = state.get("row_count")
    rows_updated = state.get("rows_updated")
    if rows_updated is None:
        rows_updated = state.get("rows_loaded")
    return (
        None if rows_inserted is None else int(rows_inserted),
        None if rows_updated is None else int(rows_updated),
    )


def _classify_job_health(
    latest_success: datetime | None,
    row_count: int | None,
    freshness_hours: int,
    *,
    latest_state: dict[str, Any] | None,
    now: datetime,
) -> StatusResult:
    latest_status = str((latest_state or {}).get("status") or "").strip().lower()
    latest_status_timestamp = _parse_timestamp((latest_state or {}).get("latest_status_timestamp_utc"))
    if latest_status == "failed":
        if latest_success is None:
            return StatusResult("red", "failed", "Latest observed job state is failed and no successful run is recorded.")
        age = now - latest_success
        if age <= timedelta(hours=freshness_hours):
            return StatusResult("yellow", "failed", "Latest observed job state failed, but the most recent successful data is still within the freshness window.")
        return StatusResult("red", "failed", "Latest observed job state failed and the last successful data is stale.")
    if latest_success is None:
        if latest_status_timestamp is not None:
            return StatusResult("yellow", "configured", "Job is configured but no successful run has been observed yet in the current dashboard sources.")
        return StatusResult("yellow", "configured", "Job is configured, but dashboard sources do not yet include a successful run timestamp.")
    if row_count is not None and row_count <= 0:
        return StatusResult("red", "zero_rows", "Job completed without any active rows in the target dataset.")
    age = now - latest_success
    if age <= timedelta(hours=freshness_hours):
        return StatusResult("green", "healthy", f"Latest successful run is within the {freshness_hours} hour freshness window.")
    if age <= timedelta(hours=freshness_hours * 2):
        return StatusResult("yellow", "stale", f"Latest successful run is outside the {freshness_hours} hour freshness window but still within the warning band.")
    return StatusResult("red", "stale", f"Latest successful run is stale beyond the {freshness_hours * 2} hour failure threshold.")


def _job_state_visibility_status() -> StatusResult:
    return StatusResult(
        "grey",
        "telemetry_pending",
        "Azure execution telemetry is not yet mirrored into dashboard job-state files. Validate this job in Azure execution history.",
    )


def _build_job_health(
    regions: list[str],
    retailer_region_rows: dict[str, dict[str, Any]],
    mfa_region_rows: dict[str, dict[str, Any]],
    *,
    now: datetime,
    job_expectations_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    job_config = load_job_expectations(job_expectations_path)
    catalogue_metrics = _catalogue_metrics()
    flat_rows: list[dict[str, Any]] = []
    by_region: dict[str, dict[str, Any]] = {
        region: {
            "summary": {
                "configuredJobs": 0,
                "healthy": 0,
                "yellow": 0,
                "red": 0,
                "grey": 0,
                "lastSuccessfulJobUtc": None,
                "worstStatus": "grey",
            },
            "jobs": [],
        }
        for region in regions
    }

    for definition in job_config.get("jobs", []):
        applicable_regions = [
            str(region).upper()
            for region in definition.get("regions", [])
            if str(region).upper() in by_region
        ]
        expected_region = str(definition.get("expectedRegion") or "GLOBAL").upper()
        state = _load_job_state(str(definition.get("stateFile") or "").strip()) if definition.get("stateFile") else None
        rows_inserted, rows_updated = _job_rows_from_state(state)
        for region in applicable_regions:
            latest_success, active_rows_after, source = _job_row_metric(
                str(definition.get("metricSource") or ""),
                region,
                retailer_region_rows,
                mfa_region_rows,
                catalogue_metrics,
            )
            if latest_success is None and state is not None:
                latest_success = _parse_timestamp(state.get("latest_success_timestamp_utc"))
            if source == "job_state" and latest_success is None and state is None:
                status = _job_state_visibility_status()
            else:
                status = _classify_job_health(
                    latest_success,
                    active_rows_after,
                    int(definition.get("freshnessHours") or 24),
                    latest_state=state,
                    now=now,
                )
            last_status_timestamp = _parse_timestamp((state or {}).get("latest_status_timestamp_utc"))
            row = {
                "region": region,
                "jobName": definition.get("jobName"),
                "jobType": definition.get("jobType"),
                "status": status.color,
                "statusLabel": status.label,
                "statusReason": status.reason,
                "schedule": definition.get("schedule"),
                "expectedRegion": expected_region,
                "lastStartedUtc": last_status_timestamp.isoformat().replace("+00:00", "Z") if last_status_timestamp else (latest_success.isoformat().replace("+00:00", "Z") if latest_success else None),
                "lastSucceededUtc": latest_success.isoformat().replace("+00:00", "Z") if latest_success else None,
                "lastFailedUtc": last_status_timestamp.isoformat().replace("+00:00", "Z") if last_status_timestamp and str((state or {}).get("status") or "").lower() == "failed" else None,
                "durationSeconds": (state or {}).get("duration_seconds"),
                "rowsInserted": rows_inserted,
                "rowsUpdated": rows_updated,
                "activeRowsAfter": active_rows_after,
                "source": source,
                "structuredLogEventName": definition.get("structuredLogEventName"),
                "azureContainerAppJobName": definition.get("jobName"),
            }
            flat_rows.append(row)
            by_region[region]["jobs"].append(row)

    for region, payload in by_region.items():
        jobs = payload["jobs"]
        jobs.sort(
            key=lambda row: (
                -STATUS_PRIORITY.get(str(row.get("status") or "grey").lower(), -1),
                str(row.get("jobType") or ""),
                str(row.get("jobName") or ""),
            )
        )
        summary = payload["summary"]
        summary["configuredJobs"] = len(jobs)
        summary["healthy"] = sum(1 for row in jobs if row["status"] == "green")
        summary["yellow"] = sum(1 for row in jobs if row["status"] == "yellow")
        summary["red"] = sum(1 for row in jobs if row["status"] == "red")
        summary["grey"] = sum(1 for row in jobs if row["status"] == "grey")
        successful_runs = [
            _parse_timestamp(row.get("lastSucceededUtc"))
            for row in jobs
            if row.get("lastSucceededUtc")
        ]
        latest_success = max((item for item in successful_runs if item is not None), default=None)
        summary["lastSuccessfulJobUtc"] = latest_success.isoformat().replace("+00:00", "Z") if latest_success else None
        summary["worstStatus"] = combine_status_colors(*(row["status"] for row in jobs)) if jobs else "grey"
    return flat_rows, by_region


def _build_job_contracts(
    regions: list[str],
    job_health_by_region: dict[str, dict[str, Any]],
    *,
    job_expectations_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    job_config = load_job_expectations(job_expectations_path)
    health_lookup = {
        (str(row.get("jobName") or ""), str(row.get("region") or "")): row
        for payload in job_health_by_region.values()
        for row in payload.get("jobs", [])
    }
    rows: list[dict[str, Any]] = []
    by_region: dict[str, list[dict[str, Any]]] = {region: [] for region in regions}
    for definition in job_config.get("jobs", []):
        contract_status = _job_contract_status(definition)
        for region in [str(item).upper() for item in definition.get("regions", []) if str(item).upper() in by_region]:
            health = health_lookup.get((str(definition.get("jobName") or ""), region), {})
            row = {
                "region": region,
                "jobName": definition.get("jobName"),
                "jobType": definition.get("jobType"),
                "contractLayer": definition.get("contractLayer"),
                "schedule": definition.get("schedule"),
                "entryScript": definition.get("entryScript"),
                "readsTables": list(definition.get("readsTables", [])),
                "writesTables": list(definition.get("writesTables", [])),
                "writesFields": list(definition.get("writesFields", [])),
                "expectedSourceOutputs": list(definition.get("expectedSourceOutputs", [])),
                "structuredLogEventName": definition.get("structuredLogEventName"),
                "lastSucceededUtc": health.get("lastSucceededUtc"),
                "currentHealth": health.get("status", "grey"),
                "currentHealthReason": health.get("statusReason"),
                "contractStatus": contract_status.color,
                "contractLabel": contract_status.label,
                "contractReason": contract_status.reason,
            }
            rows.append(row)
            by_region[region].append(row)
    for region, region_rows in by_region.items():
        region_rows.sort(
            key=lambda row: (
                -STATUS_PRIORITY.get(str(row.get("contractStatus") or "grey").lower(), -1),
                -STATUS_PRIORITY.get(str(row.get("currentHealth") or "grey").lower(), -1),
                str(row.get("jobType") or ""),
                str(row.get("jobName") or ""),
            )
        )
    rows.sort(
        key=lambda row: (
            _sort_region(str(row.get("region") or "")),
            -STATUS_PRIORITY.get(str(row.get("contractStatus") or "grey").lower(), -1),
            str(row.get("jobType") or ""),
            str(row.get("jobName") or ""),
        )
    )
    return rows, by_region


def _coverage_status(no_stock_count: int, supported_total: int) -> StatusResult:
    if supported_total <= 0:
        return StatusResult("grey", "not_applicable", "Supported coverage cannot be assessed without canonical coverage.")
    no_stock_pct = pct(no_stock_count, supported_total)
    if no_stock_pct < 20:
        return StatusResult("green", "healthy", "Market coverage is strong across supported canonical models.")
    if no_stock_pct <= 40:
        return StatusResult("yellow", "limited", "Market coverage is limited: some supported canonical models currently have no active stock in this region.")
    return StatusResult("red", "limited", "Market coverage is materially limited: many supported canonical models currently have no active stock in this region.")


def _catalogue_metrics() -> dict[str, Any]:
    models = _rows(
        """
        SELECT
            COUNT(*) AS ModelCount,
            MAX(COALESCE(UpdatedAtUtc, CreatedAtUtc)) AS LatestModelUtc
        FROM dbo.BoardModels
        WHERE IsActive = 1
        """
    )[0]
    sizes = _rows(
        """
        SELECT
            COUNT(*) AS SizeCount,
            MAX(COALESCE(UpdatedAtUtc, CreatedAtUtc)) AS LatestSizeUtc
        FROM dbo.BoardSizes
        """
    )[0]
    latest_success = max(
        filter(
            None,
            [
                _parse_timestamp(_row_field(models, "LatestModelUtc")),
                _parse_timestamp(_row_field(sizes, "LatestSizeUtc")),
            ],
        ),
        default=None,
    )
    return {
        "modelCount": int(_row_field(models, "ModelCount", 0)),
        "sizeCount": int(_row_field(sizes, "SizeCount", 0)),
        "latestSuccessUtc": latest_success.isoformat().replace("+00:00", "Z") if latest_success else None,
    }


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


def _build_supported_linkage_snapshot(conn: Any) -> dict[str, Any]:
    return supported_linkage_backfill.compute_supported_linkage_report(conn)


def _build_canonical_completeness_snapshot() -> dict[str, Any]:
    return build_canonical_catalogue_health_report()


def _empty_canonical_completeness_snapshot(reason: str) -> dict[str, Any]:
    return {
        "brands": [],
        "summary": {
            "supportedBrandCount": 0,
            "resolvedBrandCount": 0,
            "brandsMissingFromSql": [],
            "statusColor": "yellow",
            "reason": reason,
        },
    }


def _map_region_rows(rows: list[Any], region_field: str = "RegionCode") -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        region = str(_row_field(row, region_field, "<NULL>")).upper()
        mapped[region] = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    return mapped


def _map_region_model_ids(rows: list[Any], region_field: str = "RegionCode", model_field: str = "BoardModelId") -> dict[str, set[int]]:
    mapped: dict[str, set[int]] = {}
    for row in rows:
        region = str(_row_field(row, region_field, "<NULL>")).upper()
        model_id = _row_field(row, model_field)
        if model_id is None:
            continue
        mapped.setdefault(region, set()).add(int(model_id))
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


def _build_retailer_health_by_region(
    regions: list[str],
    expectations: dict[str, Any],
    retailer_matrix: list[dict[str, Any]],
    retailer_region_rows: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_region: dict[str, dict[str, Any]] = {}
    for region in regions:
        region_config = expectations.get("regions", {}).get(region, {})
        retailer_runtime = str(region_config.get("retailerRuntime") or "").strip().lower()
        configured_retailers = [
            retailer_name
            for retailer_name, config in expectations.get("retailers", {}).items()
            if config.get(region) not in {None, "not_applicable"}
        ]
        live_retailer_count = int(retailer_region_rows.get(region, {}).get("RetailerCount", 0) or 0)
        configured_count = len(configured_retailers)
        if configured_count == 0 and live_retailer_count > 0:
            configured_count = live_retailer_count
        elif retailer_runtime in {"legacy_root_runtime", "regional_live"} and live_retailer_count > configured_count:
            configured_count = live_retailer_count
        region_rows: list[dict[str, Any]] = []
        for retailer in retailer_matrix:
            cell = dict(retailer["regions"].get(region, {}))
            applicability = str(cell.get("applicability") or "not_applicable")
            if applicability == "not_applicable":
                continue
            row = {
                "retailer": retailer["retailer"],
                "statusColor": cell.get("statusColor", "grey"),
                "statusLabel": cell.get("statusLabel", "not_applicable"),
                "notes": cell.get("reason"),
                "activeRows": int(cell.get("activeRowCount", 0)),
                "availableRows": int(cell.get("availableBoardCount", 0)),
                "lastUpdatedUtc": cell.get("lastSuccessfulUpdateUtc"),
                "modelLinkPct": cell.get("linkedModelPct"),
                "sizeFamilyLinkPct": cell.get("canonicalSizeFamilyPct"),
                "exactSizeLinkPct": cell.get("exactBoardSizePct"),
                "applicability": applicability,
                "isLowLinkage": any(
                    value is not None and float(value) < 60.0
                    for value in (
                        cell.get("linkedModelPct"),
                        cell.get("canonicalSizeFamilyPct"),
                        cell.get("exactBoardSizePct"),
                    )
                ),
            }
            region_rows.append(row)

        sorted_rows = sorted(
            region_rows,
            key=lambda row: (
                -STATUS_PRIORITY.get(str(row.get("statusColor") or "grey").lower(), -1),
                -int(row.get("activeRows", 0)),
                str(row.get("retailer") or ""),
            ),
        )
        configured_count = max(configured_count, len(sorted_rows), live_retailer_count)
        status_counts = {
            "healthy": sum(1 for row in sorted_rows if row["statusColor"] == "green"),
            "yellow": sum(1 for row in sorted_rows if row["statusColor"] == "yellow"),
            "red": sum(1 for row in sorted_rows if row["statusColor"] == "red"),
            "grey": sum(1 for row in sorted_rows if row["statusColor"] == "grey"),
        }
        by_region[region] = {
            "summary": {
                "configuredRetailers": configured_count,
                "healthyRetailers": status_counts["healthy"],
                "staleRetailers": status_counts["yellow"],
                "failingRetailers": status_counts["red"],
                "notApplicableRetailers": status_counts["grey"],
                "activeRows": sum(row["activeRows"] for row in sorted_rows),
                "availableRows": sum(row["availableRows"] for row in sorted_rows),
                "averageModelLinkagePct": _average_pct([row["modelLinkPct"] for row in sorted_rows]),
                "averageSizeFamilyLinkagePct": _average_pct([row["sizeFamilyLinkPct"] for row in sorted_rows]),
                "averageExactSizeLinkagePct": _average_pct([row["exactSizeLinkPct"] for row in sorted_rows]),
                "retailerRuntime": region_config.get("retailerRuntime"),
            },
            "retailers": sorted_rows,
        }
    return by_region


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


def _clamp_pct(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(100.0, round(float(value), 2)))


def _status_score(status: str | None) -> float:
    normalized = str(status or "").lower()
    if normalized == "green":
        return 100.0
    if normalized == "yellow":
        return 70.0
    if normalized == "grey":
        return 100.0
    return 40.0


def _build_catalogue_score_lookup(
    canonical_report: dict[str, Any],
    expectations: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    brand_lookup = {
        str(item.get("brandName")): item
        for item in canonical_report.get("brands", [])
    }
    retailer_regions_by_brand: dict[str, set[str]] = {}
    for retailer_name, region_map in expectations.get("retailers", {}).items():
        del retailer_name
        for region, applicability in region_map.items():
            if applicability == "not_applicable":
                continue
            retailer_regions_by_brand.setdefault(region, set())

    per_region: dict[str, dict[str, Any]] = {}
    for region in expectations.get("regions", {}).keys():
        applicable_brands: set[str] = {
            brand
            for brand, region_map in expectations.get("mfaBrands", {}).items()
            if region_map.get(region) not in {None, "not_applicable"}
        }
        if region in retailer_regions_by_brand:
            applicable_brands.update(brand_lookup.keys())
        rows = []
        healthy = 0
        for brand in sorted(applicable_brands):
            item = brand_lookup.get(brand)
            if not item:
                rows.append(
                    {
                        "brand": brand,
                        "statusColor": "red",
                        "reason": "brand_missing_from_canonical_sql",
                        "canonicalModelCount": 0,
                        "canonicalSizeCount": 0,
                    }
                )
                continue
            suspicious = list(item.get("suspiciousModelLossIndicators") or [])
            status_color = "green" if not suspicious else "yellow"
            if status_color == "green":
                healthy += 1
            rows.append(
                {
                    "brand": brand,
                    "statusColor": status_color,
                    "reason": suspicious or ["healthy"],
                    "canonicalModelCount": int(item.get("canonicalModelCount", 0) or 0),
                    "canonicalSizeCount": int(item.get("canonicalSizeCount", 0) or 0),
                }
            )
        total = len(rows)
        score = _clamp_pct((healthy / total) * 100.0) if total else 100.0
        per_region[region] = {
            "score": score,
            "applicableBrandCount": total,
            "healthyBrandCount": healthy,
            "brands": rows,
        }
    return per_region


def _build_region_readiness(
    region_overview: list[dict[str, Any]],
    retailer_health_by_region: dict[str, dict[str, Any]],
    canonical_report: dict[str, Any],
    expectations: dict[str, Any],
    linkage_report: dict[str, Any],
) -> list[dict[str, Any]]:
    overview_lookup = {item["region"]: item for item in region_overview}
    linkage_lookup = _region_linkage_lookup(linkage_report)
    catalogue_lookup = _build_catalogue_score_lookup(canonical_report, expectations)
    readiness = []
    for region in sorted(overview_lookup.keys(), key=_sort_region):
        overview = overview_lookup[region]
        linkage = linkage_lookup.get(region, {})
        retailer_summary = retailer_health_by_region.get(region, {}).get("summary", {})
        operational = round(
            (
                _status_score(overview.get("retailerStatus"))
                + _status_score(overview.get("mfaStatus"))
                + _status_score(overview.get("overallStatus"))
            )
            / 3.0,
            2,
        )
        search = round(
            (
                _clamp_pct(linkage.get("linkedModelPctAfter")) * 0.55
                + _clamp_pct(linkage.get("linkedSizeFamilyPctAfter")) * 0.35
                + _clamp_pct(linkage.get("linkedSizePctAfter")) * 0.10
            ),
            2,
        )
        coverage = _clamp_pct(100.0 - float(overview.get("coverageGapPct") or 0.0))
        catalogue = float(catalogue_lookup.get(region, {}).get("score", 100.0))
        overall = round(
            operational * 0.35 + search * 0.30 + coverage * 0.20 + catalogue * 0.15,
            2,
        )
        readiness.append(
            {
                "region": region,
                "displayName": overview.get("displayName", region),
                "operationalScore": operational,
                "searchScore": search,
                "coverageScore": coverage,
                "catalogueScore": catalogue,
                "overallScore": overall,
                "supportedRows": int(linkage.get("supportedRows", 0) or 0),
                "supportedModelLinkPct": linkage.get("linkedModelPctAfter"),
                "canonicalSizeFamilyLinkPct": linkage.get("linkedSizeFamilyPctAfter"),
                "exactBoardSizeLinkPct": linkage.get("linkedSizePctAfter"),
                "fallbackEligibleRows": int(retailer_summary.get("availableRows", 0) or 0),
                "applicableCatalogueBrandCount": int(
                    catalogue_lookup.get(region, {}).get("applicableBrandCount", 0) or 0
                ),
                "healthyCatalogueBrandCount": int(
                    catalogue_lookup.get(region, {}).get("healthyBrandCount", 0) or 0
                ),
            }
        )
    return readiness


def _build_region_overview(
    regions: list[str],
    expectations: dict[str, Any],
    retailer_region_rows: dict[str, dict[str, Any]],
    mfa_region_rows: dict[str, dict[str, Any]],
    linkage_report: dict[str, Any],
    coverage_gaps_by_region: dict[str, dict[str, Any]],
    now: datetime,
) -> list[dict[str, Any]]:
    region_linkage = _region_linkage_lookup(linkage_report)
    overview = []
    for region in regions:
        region_config = expectations.get("regions", {}).get(region, {})
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
        coverage_row = coverage_gaps_by_region.get(region, {})
        coverage_no_stock = int(
            coverage_row.get("supportedCanonicalModelsNoStockAnywhere", {}).get("count", 0)
        )
        coverage_supported_total = int(coverage_row.get("supportedModelCount", 0))
        coverage_status = _coverage_status(coverage_no_stock, coverage_supported_total)
        operational_health_status = combine_status_colors(retailer_status.color, mfa_status.color)
        data_quality_status = search_status.color
        overview.append(
            {
                "region": region,
                "displayName": region_config.get("displayName", region),
                "statusColor": operational_health_status,
                "regionStatus": operational_health_status,
                "overallStatus": operational_health_status,
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
                "operationalHealthStatus": operational_health_status,
                "dataFreshnessStatus": operational_health_status,
                "dataQualityStatus": data_quality_status,
                "coverageQualityStatus": coverage_status.color,
                "coverageQualityReason": coverage_status.reason,
                "coverageGapPct": coverage_row.get("supportedCanonicalModelsNoStockAnywherePct"),
                "coverageSupportedModelCount": coverage_supported_total,
                "coverageNoStockAnywhereCount": coverage_no_stock,
                "retailerRuntime": region_config.get("retailerRuntime"),
                "mfaRuntime": region_config.get("mfaRuntime"),
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
        status = classify_search_health(
            linkage.get("linkedModelPctAfter"),
            linkage.get("linkedSizeFamilyPctAfter"),
            linkage.get("linkedSizePctAfter"),
        )
        rows.append(
            {
                "region": region,
                "supportedModelLinkagePct": linkage.get("linkedModelPctAfter"),
                "canonicalSizeFamilyLinkagePct": linkage.get("linkedSizeFamilyPctAfter"),
                "exactBoardSizeLinkagePct": linkage.get("linkedSizePctAfter"),
                "status": status.color,
                "statusReason": status.reason,
                "modelLinkThresholdGreen": 85.0,
                "modelLinkThresholdRed": 75.0,
                "sizeFamilyThresholdGreen": 60.0,
                "sizeFamilyThresholdRed": 40.0,
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
                "notes": "Latency/error search telemetry should be surfaced through Log Analytics workbook queries. Dashboard search quality currently uses supported linkage truth.",
            }
        )
    return sorted(rows, key=region_sort_key)


def _build_coverage_gaps(
    regions: list[str],
    supported_model_total: int,
    linkage_report: dict[str, Any],
    mfa_supported_model_ids_by_region: dict[str, set[int]],
) -> list[dict[str, Any]]:
    retailer_coverage_lookup = {
        str(item.get("regionCode") or "").upper(): {
            "projectedRetailerModelIds": {
                int(model_id)
                for model_id in item.get("projectedRetailerModelIds", [])
                if model_id is not None
            }
        }
        for item in linkage_report.get("regionCoverage", [])
    }
    supported_by_region: list[dict[str, Any]] = []
    for region in regions:
        retailer_model_ids = retailer_coverage_lookup.get(region, {}).get("projectedRetailerModelIds", set())
        mfa_model_ids = mfa_supported_model_ids_by_region.get(region, set())
        stocked_anywhere_model_ids = retailer_model_ids | mfa_model_ids
        retailer_models = len(retailer_model_ids)
        mfa_models = len(mfa_model_ids)
        stocked_anywhere_models = len(stocked_anywhere_model_ids)
        no_stock_anywhere_pct = _safe_pct(pct(max(0, supported_model_total - stocked_anywhere_models), supported_model_total))
        supported_by_region.append(
            {
                "region": region,
                "supportedModelCount": supported_model_total,
                "supportedCanonicalModelsNoActiveRetailerStock": {
                    "count": max(0, supported_model_total - retailer_models),
                    "sample": [],
                },
                "supportedCanonicalModelsNoActiveMfaStock": {
                    "count": max(0, supported_model_total - mfa_models),
                    "sample": [],
                },
                "supportedCanonicalModelsNoStockAnywhere": {
                    "count": max(0, supported_model_total - stocked_anywhere_models),
                    "sample": [],
                },
                "modelsAvailableOnlyViaMfa": {
                    "count": len(mfa_model_ids - retailer_model_ids),
                    "sample": [],
                },
                "modelsAvailableOnlyViaRetailers": {
                    "count": len(retailer_model_ids - mfa_model_ids),
                    "sample": [],
                },
                "supportedCanonicalModelsNoStockAnywherePct": no_stock_anywhere_pct,
                "brandsWithLowStockCoverage": [],
                "retailersWithLowLinkageQuality": [],
                "manufacturersWithLowLinkageQuality": [],
            }
        )
    return sorted(supported_by_region, key=region_sort_key)


def _build_alert_summary(
    region_overview: list[dict[str, Any]],
    retailer_health_by_region: dict[str, dict[str, Any]],
    mfa_matrix: list[dict[str, Any]],
    job_health_by_region: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []
    alerts_by_region: dict[str, list[dict[str, Any]]] = {region["region"]: [] for region in region_overview}
    region_lookup = {region["region"]: region for region in region_overview}

    for region in region_overview:
        region_code = region["region"]
        retailer_summary = retailer_health_by_region.get(region_code, {}).get("summary", {})
        if region["retailerStatus"] in {"yellow", "red"}:
            alert = {
                "category": "retailer_inventory",
                "alertGroup": "stale_sources",
                "severity": _alert_severity_from_status(region["retailerStatus"]),
                "statusColor": region["retailerStatus"],
                "region": region_code,
                "title": f"{region_code} retailer inventory needs attention",
                "message": region["retailerReason"],
                "affectedRetailers": retailer_summary.get("configuredRetailers", 0),
                "metricName": "retailerFreshness",
                "currentValue": region.get("lastRetailerInventoryRefreshUtc"),
                "threshold": "24h green / 48h red",
                "sourceType": "sql_freshness",
                "reason": region["retailerReason"],
                "suggestedAction": f"Review the {region_code} retailer refresh job and stale retailer sources.",
            }
            alerts.append(alert)
            alerts_by_region[region_code].append(alert)
        if region["mfaStatus"] in {"yellow", "red"}:
            alert = {
                "category": "manufacturer_availability",
                "alertGroup": "stale_sources",
                "severity": _alert_severity_from_status(region["mfaStatus"]),
                "statusColor": region["mfaStatus"],
                "region": region_code,
                "title": f"{region_code} manufacturer availability needs attention",
                "message": region["mfaReason"],
                "metricName": "mfaFreshness",
                "currentValue": region.get("lastMfaRefreshUtc"),
                "threshold": "24h green / 48h red",
                "sourceType": "sql_freshness",
                "reason": region["mfaReason"],
                "suggestedAction": f"Review the {region_code} manufacturer availability job and degraded brand sources.",
            }
            alerts.append(alert)
            alerts_by_region[region_code].append(alert)
        if region["searchHealthStatus"] in {"yellow", "red"}:
            alert = {
                "category": "search_quality",
                "alertGroup": "linkage_warnings",
                "severity": _alert_severity_from_status(region["searchHealthStatus"]),
                "statusColor": region["searchHealthStatus"],
                "region": region_code,
                "title": f"{region_code} search quality below target",
                "message": region["searchHealthReason"],
                "metricName": "modelLinkPct",
                "currentValue": region.get("supportedModelLinkagePct"),
                "threshold": 85.0 if region["searchHealthStatus"] == "yellow" else 75.0,
                "sourceType": "supported_linkage_truth",
                "reason": region["searchHealthReason"],
                "suggestedAction": f"Improve {region_code} supported-manufacturer brand/model parsing and size-family linkage.",
            }
            alerts.append(alert)
            alerts_by_region[region_code].append(alert)
        if region.get("coverageQualityStatus") in {"yellow", "red"}:
            no_stock_count = region.get("coverageNoStockAnywhereCount")
            supported_count = region.get("coverageSupportedModelCount")
            coverage_pct = region.get("coverageGapPct")
            if no_stock_count is not None and supported_count:
                coverage_message = (
                    f"{no_stock_count} of {supported_count} supported canonical models "
                    f"currently have no active stock in this region"
                )
                if coverage_pct is not None:
                    coverage_message += f" ({coverage_pct}%)."
                else:
                    coverage_message += "."
            else:
                coverage_message = region.get("coverageQualityReason")
            alert = {
                "category": "market_coverage",
                "alertGroup": "linkage_warnings",
                "severity": _alert_severity_from_status(region["coverageQualityStatus"]),
                "statusColor": region["coverageQualityStatus"],
                "region": region_code,
                "title": f"{region_code} market coverage limited",
                "message": coverage_message,
                "metricName": "noStockAnywherePct",
                "currentValue": coverage_pct,
                "threshold": 20.0 if region.get("coverageQualityStatus") == "yellow" else 40.0,
                "sourceType": "supported_linkage_truth",
                "reason": region.get("coverageQualityReason"),
                "suggestedAction": f"Review supported {region_code} model coverage, retailer reach, and whether the gap reflects a genuine market limitation.",
            }
            alerts.append(alert)
            alerts_by_region[region_code].append(alert)

    for region_code, payload in retailer_health_by_region.items():
        region_status = region_lookup.get(region_code, {})
        if region_status.get("retailerStatus") in {"yellow", "red"}:
            continue
        for retailer in payload.get("retailers", []):
            if retailer["statusColor"] == "red":
                alert = {
                    "category": "retailer_source",
                    "alertGroup": "critical",
                    "severity": "critical",
                "statusColor": "red",
                "region": region_code,
                "source": retailer["retailer"],
                "title": f"{retailer['retailer']} failing in {region_code}",
                "message": retailer["notes"],
                "metricName": "retailerFreshness",
                "currentValue": retailer.get("lastUpdatedUtc"),
                "threshold": "24h green / 48h red",
                "sourceType": "retailer_health",
                "reason": retailer["notes"],
                "suggestedAction": f"Review {retailer['retailer']} source health in {region_code}.",
            }
                alerts.append(alert)
                alerts_by_region.setdefault(region_code, []).append(alert)

    for brand in mfa_matrix:
        for region_code, cell in brand["regions"].items():
            if region_lookup.get(region_code, {}).get("mfaStatus") in {"yellow", "red"}:
                continue
            if cell["statusColor"] == "red":
                alert = {
                    "category": "mfa_source",
                    "alertGroup": "critical",
                    "severity": "critical",
                "statusColor": "red",
                "region": region_code,
                "source": brand["brand"],
                "title": f"{brand['brand']} failing in {region_code}",
                "message": cell["reason"],
                "metricName": "mfaFreshness",
                "currentValue": cell.get("lastSuccessfulUpdateUtc"),
                "threshold": "24h green / 48h red",
                "sourceType": "mfa_health",
                "reason": cell["reason"],
                "suggestedAction": f"Review {brand['brand']} manufacturer direct source health in {region_code}.",
            }
                alerts.append(alert)
                alerts_by_region.setdefault(region_code, []).append(alert)

    for region_code, payload in (job_health_by_region or {}).items():
        for job in payload.get("jobs", []):
            if job.get("status") not in {"yellow", "red"}:
                continue
            if job.get("expectedRegion") == "GLOBAL" and job.get("status") == "yellow":
                continue
            alert = {
                "category": "job_health",
                "alertGroup": "critical" if job["status"] == "red" else "stale_sources",
                "severity": _alert_severity_from_status(job["status"]),
                "statusColor": job["status"],
                "region": region_code,
                "source": job.get("jobName"),
                "title": f"{region_code} job attention required: {job.get('jobType', 'job')}",
                "message": job.get("statusReason") or f"{job.get('jobName')} requires attention.",
                "metricName": "jobFreshness",
                "currentValue": job.get("lastSucceededUtc"),
                "threshold": job.get("schedule"),
                "sourceType": "job_health",
                "reason": job.get("statusReason"),
                "suggestedAction": f"Review Azure Container App Job {job.get('jobName')} for {region_code}.",
            }
            alerts.append(alert)
            alerts_by_region.setdefault(region_code, []).append(alert)

    grouped_counts = {
        "critical": sum(1 for alert in alerts if alert["severity"] == "critical"),
        "warnings": sum(1 for alert in alerts if alert["severity"] == "warning"),
        "staleSources": sum(1 for alert in alerts if alert["alertGroup"] == "stale_sources"),
        "linkageWarnings": sum(1 for alert in alerts if alert["alertGroup"] == "linkage_warnings"),
    }
    sorted_alerts = sorted(
        alerts,
        key=lambda alert: (
            -SEVERITY_PRIORITY.get(alert["severity"], -1),
            -STATUS_PRIORITY.get(str(alert.get("statusColor") or "grey").lower(), -1),
            str(alert.get("region") or ""),
            str(alert.get("source") or alert.get("title") or ""),
        ),
    )
    return {
        "summary": grouped_counts,
        "topAlerts": sorted_alerts[:10],
        "allAlerts": sorted_alerts,
        "byRegion": {region: sorted(items, key=lambda alert: (-SEVERITY_PRIORITY.get(alert["severity"], -1), str(alert.get("title") or ""))) for region, items in alerts_by_region.items()},
    }


def _build_region_details(
    regions: list[str],
    region_overview: list[dict[str, Any]],
    inventory_counts: list[dict[str, Any]],
    search_quality: list[dict[str, Any]],
    coverage_gaps: list[dict[str, Any]],
    retailer_health_by_region: dict[str, dict[str, Any]],
    mfa_matrix: list[dict[str, Any]],
    alert_summary: dict[str, Any],
    job_health_by_region: dict[str, dict[str, Any]],
    job_contracts_by_region: dict[str, list[dict[str, Any]]],
    readiness_rows: list[dict[str, Any]],
    canonical_report: dict[str, Any],
) -> dict[str, Any]:
    overview_lookup = {row["region"]: row for row in region_overview}
    inventory_lookup = {row["region"]: row for row in inventory_counts}
    search_lookup = {row["region"]: row for row in search_quality}
    coverage_lookup = {row["region"]: row for row in coverage_gaps}
    readiness_lookup = {row["region"]: row for row in readiness_rows}
    region_details: dict[str, Any] = {}
    for region in regions:
        region_details[region] = {
            "region": region,
            "overview": overview_lookup.get(region, {}),
            "readiness": readiness_lookup.get(region, {}),
            "inventoryCounts": inventory_lookup.get(region, {}),
            "searchQuality": search_lookup.get(region, {}),
            "coverageGaps": coverage_lookup.get(region, {}),
            "retailerHealth": retailer_health_by_region.get(region, {"summary": {}, "retailers": []}),
            "jobHealth": job_health_by_region.get(region, {"summary": {}, "jobs": []}),
            "jobContracts": job_contracts_by_region.get(region, []),
            "mfaHealth": [
                {
                    "brand": item["brand"],
                    **item["regions"].get(region, {}),
                }
                for item in mfa_matrix
                if item["regions"].get(region, {}).get("applicability") != "not_applicable"
            ],
            "canonicalCompleteness": canonical_report,
            "alerts": alert_summary.get("byRegion", {}).get(region, []),
        }
    return region_details


def _latest_job_issue(
    rows: list[dict[str, Any]],
    *,
    include_global: bool = False,
) -> str:
    relevant = []
    for row in rows or []:
        expected_region = str(row.get("expectedRegion") or "").upper()
        if expected_region == "GLOBAL" and not include_global:
            continue
        if row.get("status") in {"yellow", "red"}:
            relevant.append(row)
    if not relevant:
        return "No current issues."
    relevant.sort(
        key=lambda row: (
            -STATUS_PRIORITY.get(str(row.get("status") or "grey").lower(), -1),
            str(row.get("jobName") or ""),
        )
    )
    item = relevant[0]
    return f"{item.get('jobName')}: {item.get('statusReason') or item.get('statusLabel') or item.get('status')}"


def _build_pipeline_health(
    region_overview: list[dict[str, Any]],
    job_health: list[dict[str, Any]],
    alert_summary: dict[str, Any],
    *,
    cache_health_color: str,
    cache_health_reason: str,
) -> list[dict[str, Any]]:
    global_jobs = [
        row
        for row in (job_health or [])
        if str(row.get("expectedRegion") or "").upper() == "GLOBAL"
    ]
    global_catalogue_job = next(
        (row for row in global_jobs if row.get("jobName") == "quivrr-weekly-brand-catalogues"),
        None,
    )
    catalogue_status = "grey"
    catalogue_reason = "Weekly canonical telemetry is unavailable."
    catalogue_metric = "No recent global canonical execution"
    if global_catalogue_job:
        catalogue_status = str(global_catalogue_job.get("status") or "grey").lower()
        catalogue_reason = (
            global_catalogue_job.get("statusReason")
            or "Weekly canonical telemetry is unavailable."
        )
        latest_success = global_catalogue_job.get("lastSucceededUtc")
        catalogue_metric = (
            f"Last success {latest_success}"
            if latest_success
            else "No recent global canonical success"
        )
        if catalogue_status == "yellow":
            catalogue_reason = (
                f"{catalogue_reason} Canonical truth preserved; review guarded source outputs in Azure."
            )

    mfa_regions = [row for row in region_overview if row.get("mfaStatus") in {"green", "yellow", "red"}]
    retailer_regions = [row for row in region_overview if row.get("retailerStatus") in {"green", "yellow", "red"}]
    search_regions = [row for row in region_overview if row.get("searchHealthStatus") in {"green", "yellow", "red"}]
    linkage_regions = [row for row in region_overview if row.get("dataQualityStatus") in {"green", "yellow", "red"}]

    def summarize_region_stage(rows: list[dict[str, Any]], status_key: str, reason_key: str, metric_key: str, metric_label: str) -> tuple[str, str, str]:
        if not rows:
            return "grey", "No regional telemetry available.", f"No {metric_label}"
        color = combine_status_colors(*(str(row.get(status_key) or "grey").lower() for row in rows))
        issues = [row for row in rows if str(row.get(status_key) or "").lower() in {"yellow", "red"}]
        reason = "All expected regions are healthy."
        if issues:
            issues.sort(
                key=lambda row: (
                    -STATUS_PRIORITY.get(str(row.get(status_key) or "grey").lower(), -1),
                    str(row.get("region") or ""),
                )
            )
            issue = issues[0]
            reason = f"{issue.get('region')}: {issue.get(reason_key) or issue.get(status_key)}"
        metric = ", ".join(
            f"{row.get('region')} {metric_label} {row.get(metric_key) if row.get(metric_key) is not None else 'n/a'}"
            for row in rows
        )
        return color, reason, metric

    mfa_status, mfa_reason, mfa_metric = summarize_region_stage(
        mfa_regions,
        "mfaStatus",
        "mfaReason",
        "activeMfaBoardCount",
        "boards",
    )
    retailer_status, retailer_reason, retailer_metric = summarize_region_stage(
        retailer_regions,
        "retailerStatus",
        "retailerReason",
        "activeRetailerBoardCount",
        "boards",
    )
    linkage_status, linkage_reason, linkage_metric = summarize_region_stage(
        linkage_regions,
        "dataQualityStatus",
        "searchHealthReason",
        "supportedModelLinkagePct",
        "model%",
    )
    search_status, search_reason, search_metric = summarize_region_stage(
        search_regions,
        "searchHealthStatus",
        "searchHealthReason",
        "canonicalSizeFamilyLinkagePct",
        "family%",
    )

    alerts_summary = alert_summary.get("summary", {}) if isinstance(alert_summary, dict) else {}
    operations_metric = (
        f"Critical {alerts_summary.get('critical', 0)} · Warnings {alerts_summary.get('warnings', 0)}"
    )

    return [
        {
            "key": "global_canonical",
            "label": "Global Canonical",
            "status": catalogue_status,
            "lastSuccessUtc": global_catalogue_job.get("lastSucceededUtc") if global_catalogue_job else None,
            "latestIssue": catalogue_reason,
            "primaryMetric": catalogue_metric,
            "anchor": "#job-health",
        },
        {
            "key": "regional_mfa",
            "label": "Regional Manufacturer Availability",
            "status": mfa_status,
            "lastSuccessUtc": max((row.get("lastMfaRefreshUtc") for row in mfa_regions if row.get("lastMfaRefreshUtc")), default=None),
            "latestIssue": mfa_reason,
            "primaryMetric": mfa_metric,
            "anchor": "#mfa-health",
        },
        {
            "key": "regional_retailer_inventory",
            "label": "Regional Retailer Inventory",
            "status": retailer_status,
            "lastSuccessUtc": max((row.get("lastRetailerInventoryRefreshUtc") for row in retailer_regions if row.get("lastRetailerInventoryRefreshUtc")), default=None),
            "latestIssue": retailer_reason,
            "primaryMetric": retailer_metric,
            "anchor": "#retailer-health",
        },
        {
            "key": "linkage_quality",
            "label": "Linkage Quality",
            "status": linkage_status,
            "lastSuccessUtc": None,
            "latestIssue": linkage_reason,
            "primaryMetric": linkage_metric,
            "anchor": "#link-quality",
        },
        {
            "key": "search_health",
            "label": "Search Health",
            "status": search_status,
            "lastSuccessUtc": None,
            "latestIssue": search_reason,
            "primaryMetric": search_metric,
            "anchor": "#search-quality",
        },
        {
            "key": "operations_centre",
            "label": "Operations Centre",
            "status": cache_health_color,
            "lastSuccessUtc": None,
            "latestIssue": cache_health_reason,
            "primaryMetric": operations_metric,
            "anchor": "#alerts",
        },
        {
            "key": "bodhi",
            "label": "Future: Bodhi",
            "status": "grey",
            "lastSuccessUtc": None,
            "latestIssue": "Future layer only. Bodhi is not active in the public Operations Centre.",
            "primaryMetric": "Future layer",
            "anchor": None,
        },
    ]


def build_operations_dashboard_metrics(
    *,
    generated_at_utc: str | None = None,
    now: datetime | None = None,
    expectations_path: Path | None = None,
    job_expectations_path: Path | None = None,
    linkage_report_builder: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    expectations = load_source_expectations(expectations_path)
    generated_at_utc = generated_at_utc or utc_timestamp()
    now = now or _utcnow()
    linkage_report_builder = linkage_report_builder or _build_supported_linkage_snapshot

    retailer_region_rows = _map_region_rows(_rows(RETAILER_REGION_QUERY))
    mfa_region_rows = _map_region_rows(_rows(MFA_REGION_QUERY))
    retailer_health_rows = _rows(RETAILER_HEALTH_QUERY)
    mfa_health_rows = _rows(MFA_HEALTH_QUERY)
    supported_counts_rows = _rows(SUPPORTED_COUNTS_QUERY)
    supported_counts = _map_region_rows(supported_counts_rows)
    supported_model_total_row = (_rows(SUPPORTED_MODEL_TOTAL_QUERY) or [{}])[0]
    supported_model_total = int(_row_field(supported_model_total_row, "SupportedModelCount", 0) or 0)
    supported_mfa_model_ids_by_region = _map_region_model_ids(_rows(SUPPORTED_MFA_MODEL_IDS_QUERY))

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
    try:
        canonical_report = _build_canonical_completeness_snapshot()
    except Exception as exc:
        canonical_report = _empty_canonical_completeness_snapshot(
            f"canonical_completeness_unavailable:{type(exc).__name__}"
        )
    with engine.begin() as conn:
        linkage_report = linkage_report_builder(conn)

    retailer_matrix = _build_retailer_matrix(regions, expectations, retailer_health_rows, linkage_report, now)
    retailer_health_by_region = _build_retailer_health_by_region(regions, expectations, retailer_matrix, retailer_region_rows)
    mfa_matrix = _build_mfa_matrix(regions, expectations, mfa_health_rows, linkage_report, now)
    job_health, job_health_by_region = _build_job_health(
        regions,
        retailer_region_rows,
        mfa_region_rows,
        now=now,
        job_expectations_path=job_expectations_path,
    )
    job_contracts, job_contracts_by_region = _build_job_contracts(
        regions,
        job_health_by_region,
        job_expectations_path=job_expectations_path,
    )
    coverage_gaps = _build_coverage_gaps(
        regions,
        supported_model_total,
        linkage_report,
        supported_mfa_model_ids_by_region,
    )
    coverage_gaps_by_region = {row["region"]: row for row in coverage_gaps}
    region_overview = _build_region_overview(regions, expectations, retailer_region_rows, mfa_region_rows, linkage_report, coverage_gaps_by_region, now)
    inventory_counts = _build_inventory_counts(regions, retailer_region_rows, mfa_region_rows, supported_counts)
    search_quality = _build_search_quality(regions, linkage_report)
    readiness = _build_region_readiness(
        region_overview,
        retailer_health_by_region,
        canonical_report,
        expectations,
        linkage_report,
    )
    alert_summary = _build_alert_summary(region_overview, retailer_health_by_region, mfa_matrix, job_health_by_region)
    region_details = _build_region_details(
        regions,
        region_overview,
        inventory_counts,
        search_quality,
        coverage_gaps,
        retailer_health_by_region,
        mfa_matrix,
        alert_summary,
        job_health_by_region,
        job_contracts_by_region,
        readiness,
        canonical_report,
    )
    pipeline_health = _build_pipeline_health(
        region_overview,
        job_health,
        alert_summary,
        cache_health_color="green",
        cache_health_reason="Complete live payload is available.",
    )

    return {
        "generatedAtUtc": generated_at_utc,
        "service": SERVICE_NAME,
        "version": DASHBOARD_VERSION,
        "regions": regions,
        "regionOverview": region_overview,
        "mfaHealth": mfa_matrix,
        "retailerHealth": retailer_matrix,
        "retailerHealthByRegion": retailer_health_by_region,
        "jobHealth": job_health,
        "jobHealthByRegion": job_health_by_region,
        "jobContracts": job_contracts,
        "jobContractsByRegion": job_contracts_by_region,
        "inventoryCounts": inventory_counts,
        "searchQuality": search_quality,
        "regionalReadiness": readiness,
        "canonicalCompleteness": canonical_report,
        "pipelineHealth": pipeline_health,
        "coverageGaps": coverage_gaps,
        "topUnmatchedModels": linkage_report.get("topRemainingUnmatchedModels", []),
        "topUnmatchedRetailers": linkage_report.get("topUnmatchedRetailers", []),
        "alerts": alert_summary["topAlerts"],
        "alertSummary": alert_summary,
        "regionDetails": region_details,
        "sourceExpectations": expectations,
        "linkQuality": linkage_report,
    }
