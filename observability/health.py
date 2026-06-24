from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from sqlalchemy import text

from market_intelligence.db import execute_with_retry
from utils.structured_logging import STATE_DIR


REGIONS = ("AU", "EU", "ID")
FRESHNESS_WINDOWS_HOURS = {
    "inventory": 36,
    "mfa": 72,
    "catalogue": 168,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
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


def link_quality(linked_rows: int, total_rows: int) -> float:
    if total_rows <= 0:
        return 0.0
    return round(linked_rows / total_rows, 4)


def _status_from_freshness(
    latest_success: datetime | None,
    freshness_hours: int,
    latest_state: dict[str, Any] | None = None,
    dependency_failed: bool = False,
) -> tuple[str, str]:
    if dependency_failed:
        return "Critical", "A required dependency is unavailable."
    if latest_success is None:
        return "High", "No successful run timestamp is available."

    stale_after = _utcnow() - timedelta(hours=freshness_hours)
    within_window = latest_success >= stale_after
    if latest_state:
        latest_status = str(latest_state.get("status") or "").lower()
        consecutive_failures = int(latest_state.get("consecutive_failures") or 0)
        if latest_status == "failed" and within_window:
            if consecutive_failures >= 2:
                return "High", "Latest two scheduled runs failed."
            return "Warning", "Latest run failed but data is still fresh."
    if not within_window:
        return "High", f"Latest successful run is outside the {freshness_hours} hour freshness window."
    return "Healthy", "Latest successful run is inside the freshness window."


def _load_job_state(job_name: str) -> dict[str, Any] | None:
    path = STATE_DIR / f"{job_name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _rows(query: str, params: dict[str, Any] | None = None) -> list[Any]:
    return execute_with_retry(text(query), params or {})


def _retailer_inventory_metrics() -> dict[str, dict[str, Any]]:
    rows = _rows(
        """
        SELECT
            ri.RegionCode,
            COUNT(*) AS InventoryRows,
            SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRows,
            SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRows,
            COUNT(DISTINCT ri.RetailerId) AS RetailerCoverage,
            MAX(COALESCE(ri.LastCheckedUtc, ri.UpdatedAtUtc, ri.CreatedAtUtc)) AS LatestCheckedUtc
        FROM dbo.RetailerInventory ri
        WHERE ri.IsActive = 1
        GROUP BY ri.RegionCode
        """
    )
    metrics = {region: {"inventoryRows": 0, "linkedModelRows": 0, "linkedSizeRows": 0, "retailerCoverage": 0, "latestCheckedUtc": None} for region in REGIONS}
    for row in rows:
        region = str(row.RegionCode or "").upper()
        if region not in metrics:
            continue
        metrics[region] = {
            "inventoryRows": int(row.InventoryRows or 0),
            "linkedModelRows": int(row.LinkedModelRows or 0),
            "linkedSizeRows": int(row.LinkedSizeRows or 0),
            "retailerCoverage": int(row.RetailerCoverage or 0),
            "latestCheckedUtc": row.LatestCheckedUtc,
        }
    return metrics


def _manufacturer_inventory_metrics() -> dict[str, dict[str, Any]]:
    rows = _rows(
        """
        SELECT
            mi.RegionCode,
            COUNT(*) AS InventoryRows,
            SUM(CASE WHEN mi.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRows,
            SUM(CASE WHEN mi.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRows,
            COUNT(DISTINCT mi.BrandId) AS BrandCoverage,
            MAX(COALESCE(mi.LastCheckedUtc, mi.UpdatedAtUtc, mi.CreatedAtUtc)) AS LatestCheckedUtc
        FROM dbo.ManufacturerInventory mi
        WHERE COALESCE(mi.IsActive, 1) = 1
        GROUP BY mi.RegionCode
        """
    )
    metrics = {region: {"inventoryRows": 0, "linkedModelRows": 0, "linkedSizeRows": 0, "brandCoverage": 0, "latestCheckedUtc": None} for region in REGIONS}
    for row in rows:
        region = str(row.RegionCode or "").upper()
        if region not in metrics:
            continue
        metrics[region] = {
            "inventoryRows": int(row.InventoryRows or 0),
            "linkedModelRows": int(row.LinkedModelRows or 0),
            "linkedSizeRows": int(row.LinkedSizeRows or 0),
            "brandCoverage": int(row.BrandCoverage or 0),
            "latestCheckedUtc": row.LatestCheckedUtc,
        }
    return metrics


def _null_region_counts() -> dict[str, int]:
    retailer = _rows("SELECT COUNT(*) AS NullRows FROM dbo.RetailerInventory WHERE RegionCode IS NULL")[0].NullRows
    manufacturer = _rows("SELECT COUNT(*) AS NullRows FROM dbo.ManufacturerInventory WHERE RegionCode IS NULL")[0].NullRows
    return {
        "retailerInventoryNullRegionRows": int(retailer or 0),
        "manufacturerInventoryNullRegionRows": int(manufacturer or 0),
    }


def _region_leakage_counts() -> dict[str, int]:
    retailer = _rows(
        """
        SELECT COUNT(*) AS LeakageRows
        FROM dbo.RetailerInventory ri
        INNER JOIN dbo.Retailers r ON r.RetailerId = ri.RetailerId
        WHERE ri.IsActive = 1
          AND ri.RegionCode IS NOT NULL
          AND r.RegionCode IS NOT NULL
          AND ri.RegionCode <> r.RegionCode
        """
    )[0].LeakageRows
    return {"retailerRegionLeakageRows": int(retailer or 0)}


def _inventory_drop_checks() -> dict[str, Any]:
    rows = _rows(
        """
        WITH snapshots AS (
            SELECT
                s.SnapshotDate,
                r.RegionCode,
                COUNT(*) AS SnapshotRows
            FROM dbo.RetailerInventorySnapshot s
            INNER JOIN dbo.Retailers r ON r.RetailerId = s.RetailerId
            GROUP BY s.SnapshotDate, r.RegionCode
        ),
        ranked AS (
            SELECT
                SnapshotDate,
                RegionCode,
                SnapshotRows,
                ROW_NUMBER() OVER (PARTITION BY RegionCode ORDER BY SnapshotDate DESC) AS rn
            FROM snapshots
        )
        SELECT
            cur.RegionCode,
            cur.SnapshotRows AS CurrentRows,
            prev.SnapshotRows AS PreviousRows
        FROM ranked cur
        LEFT JOIN ranked prev
            ON prev.RegionCode = cur.RegionCode
           AND prev.rn = 2
        WHERE cur.rn = 1
        """
    )
    output = {}
    for row in rows:
        current = int(row.CurrentRows or 0)
        previous = int(row.PreviousRows or 0)
        drop_rate = 0.0 if previous <= 0 else round((previous - current) / previous, 4)
        output[str(row.RegionCode)] = {
            "currentRows": current,
            "previousRows": previous,
            "dropRate": drop_rate,
            "dropDetected": previous > 0 and current < previous,
        }
    return output


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
    latest_success = max(filter(None, [_parse_timestamp(models.LatestModelUtc), _parse_timestamp(sizes.LatestSizeUtc)]), default=None)
    state = _load_job_state("weekly_brand_catalogues")
    status, reason = _status_from_freshness(latest_success, FRESHNESS_WINDOWS_HOURS["catalogue"], latest_state=state)
    return {
        "status": status,
        "reason": reason,
        "modelCount": int(models.ModelCount or 0),
        "sizeCount": int(sizes.SizeCount or 0),
        "latestSuccessUtc": latest_success.isoformat().replace("+00:00", "Z") if latest_success else None,
    }


def _http_health(url: str) -> tuple[bool, dict[str, Any] | None]:
    try:
        with urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8")
        return True, json.loads(body)
    except (URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return False, None


def _bodhi_health() -> dict[str, Any]:
    url = os.getenv("BOARD_GUIDE_HEALTH_URL", "http://127.0.0.1:8090/api/health")
    ok, payload = _http_health(url)
    if not ok or not payload:
        return {
            "status": "Critical",
            "reason": "Board Guide API health endpoint is unavailable.",
            "healthUrl": url,
        }
    if not payload.get("azure_openai_configured"):
        return {
            "status": "Critical",
            "reason": "Azure OpenAI is not configured for Board Guide.",
            "healthUrl": url,
        }
    return {
        "status": "Healthy",
        "reason": "Board Guide health endpoint responded and Azure OpenAI is configured.",
        "healthUrl": url,
    }


def _region_health_row(region: str, retailer: dict[str, Any], manufacturer: dict[str, Any]) -> dict[str, Any]:
    retailer_latest = _parse_timestamp(retailer.get("latestCheckedUtc"))
    manufacturer_latest = _parse_timestamp(manufacturer.get("latestCheckedUtc"))
    inventory_status, inventory_reason = _status_from_freshness(
        retailer_latest,
        FRESHNESS_WINDOWS_HOURS["inventory"],
        latest_state=_load_job_state(f"inventory_{region.lower()}"),
    )
    mfa_status, mfa_reason = _status_from_freshness(
        manufacturer_latest,
        FRESHNESS_WINDOWS_HOURS["mfa"],
        latest_state=_load_job_state(f"mfa_{region.lower()}"),
    )
    if "Critical" in {inventory_status, mfa_status}:
        status = "Critical"
    elif "High" in {inventory_status, mfa_status}:
        status = "High"
    elif "Warning" in {inventory_status, mfa_status}:
        status = "Warning"
    else:
        status = "Healthy"
    return {
        "region": region,
        "status": status,
        "inventoryStatus": inventory_status,
        "inventoryReason": inventory_reason,
        "mfaStatus": mfa_status,
        "mfaReason": mfa_reason,
        "retailerInventoryRows": retailer.get("inventoryRows", 0),
        "manufacturerInventoryRows": manufacturer.get("inventoryRows", 0),
        "retailerModelLinkRate": link_quality(retailer.get("linkedModelRows", 0), retailer.get("inventoryRows", 0)),
        "retailerSizeLinkRate": link_quality(retailer.get("linkedSizeRows", 0), retailer.get("inventoryRows", 0)),
        "manufacturerModelLinkRate": link_quality(manufacturer.get("linkedModelRows", 0), manufacturer.get("inventoryRows", 0)),
        "manufacturerSizeLinkRate": link_quality(manufacturer.get("linkedSizeRows", 0), manufacturer.get("inventoryRows", 0)),
        "retailerCoverage": retailer.get("retailerCoverage", 0),
        "brandCoverage": manufacturer.get("brandCoverage", 0),
    }


def collect_health_snapshot() -> dict[str, Any]:
    retailer_metrics = _retailer_inventory_metrics()
    manufacturer_metrics = _manufacturer_inventory_metrics()
    null_regions = _null_region_counts()
    leakage = _region_leakage_counts()
    drop_checks = _inventory_drop_checks()
    catalogue = _catalogue_metrics()
    bodhi = _bodhi_health()

    inventory_regions = {
        region: _region_health_row(region, retailer_metrics[region], manufacturer_metrics[region])
        for region in REGIONS
    }
    open_issues: list[str] = []
    for region, item in inventory_regions.items():
        if item["status"] != "Healthy":
            open_issues.append(f"{region} region health is {item['status']}: {item['inventoryReason']} / {item['mfaReason']}")
        if item["retailerModelLinkRate"] < 0.8:
            open_issues.append(f"{region} retailer BoardModelId link quality is below target.")
        if item["manufacturerModelLinkRate"] < 0.8 and item["manufacturerInventoryRows"] > 0:
            open_issues.append(f"{region} manufacturer BoardModelId link quality is below target.")
    if null_regions["retailerInventoryNullRegionRows"] or null_regions["manufacturerInventoryNullRegionRows"]:
        open_issues.append("Null RegionCode rows detected in inventory tables.")
    if leakage["retailerRegionLeakageRows"]:
        open_issues.append("Retailer region leakage detected.")
    if bodhi["status"] != "Healthy":
        open_issues.append(bodhi["reason"])
    recommended_actions = []
    if leakage["retailerRegionLeakageRows"]:
        recommended_actions.append("Investigate region leakage before the next scheduled refresh.")
    if any(item["status"] in {"High", "Critical"} for item in inventory_regions.values()):
        recommended_actions.append("Review the latest regional job logs and freshness windows in Log Analytics.")
    if bodhi["status"] != "Healthy":
        recommended_actions.append("Check Board Guide API health and Azure OpenAI configuration.")
    if not recommended_actions:
        recommended_actions.append("No urgent intervention required; continue monitoring scheduled runs.")

    platform_status = "Healthy"
    if bodhi["status"] == "Critical":
        platform_status = "Critical"
    elif any(item["status"] == "High" for item in inventory_regions.values()) or catalogue["status"] == "High":
        platform_status = "High"
    elif any(item["status"] == "Warning" for item in inventory_regions.values()):
        platform_status = "Warning"

    return {
        "generatedAtUtc": _utcnow().replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "platformHealth": {
            "status": platform_status,
            "reason": "Derived from current regional freshness, leakage checks, and Bodhi dependency health.",
        },
        "regionHealth": list(inventory_regions.values()),
        "catalogueHealth": catalogue,
        "inventoryHealth": {
            "byRegion": retailer_metrics,
            "nullRegionCounts": null_regions,
            "dropChecks": drop_checks,
            "regionLeakage": leakage,
        },
        "mfaHealth": {
            "byRegion": manufacturer_metrics,
            "nullRegionCounts": null_regions,
        },
        "bodhiHealth": bodhi,
        "openIssues": open_issues,
        "recommendedActions": recommended_actions,
    }
