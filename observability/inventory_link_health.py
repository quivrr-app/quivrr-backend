from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from market_intelligence.db import execute_with_retry
from utils.structured_logging import utc_timestamp


SERVICE_NAME = "inventory_link_health"

SNAPSHOT_QUERY = """
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>') AS RegionCode,
    COUNT(*) AS TotalRows,
    SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRows,
    SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRows,
    COUNT(DISTINCT r.RetailerId) AS RetailerCount
FROM dbo.RetailerInventory ri
INNER JOIN dbo.Retailers r
    ON r.RetailerId = ri.RetailerId
WHERE ri.IsActive = 1
GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>')
"""

RETAILER_QUERY = """
SELECT
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>') AS RegionCode,
    r.RetailerName,
    COUNT(*) AS TotalRows,
    SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModelRows,
    SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizeRows
FROM dbo.RetailerInventory ri
INNER JOIN dbo.Retailers r
    ON r.RetailerId = ri.RetailerId
WHERE ri.IsActive = 1
GROUP BY
    COALESCE(NULLIF(LTRIM(RTRIM(ri.RegionCode)), ''), '<NULL>'),
    r.RetailerName
"""

REGION_PRIORITY = {
    "EU": 0,
    "AU": 1,
    "ID": 2,
    "US": 3,
}


def link_pct(linked_rows: int, total_rows: int) -> float:
    if total_rows <= 0:
        return 0.0
    return round((linked_rows / total_rows) * 100, 2)


def _field(row: Any, name: str, default: Any = None) -> Any:
    if hasattr(row, name):
        value = getattr(row, name)
        return default if value is None else value
    if isinstance(row, dict):
        value = row.get(name, default)
        return default if value is None else value
    return default


def _region_sort_key(region: str) -> tuple[int, str]:
    clean_region = str(region or "").upper()
    return (REGION_PRIORITY.get(clean_region, 99), clean_region)


def _retailer_sort_key(region: str, retailer_name: str) -> tuple[int, str, str]:
    return (_region_sort_key(region)[0], str(region or "").upper(), str(retailer_name or "").lower())


def build_snapshot_payload(
    region: str,
    total_rows: int,
    linked_model_rows: int,
    linked_size_rows: int,
    retailer_count: int,
    generated_at_utc: str | None = None,
    service: str = SERVICE_NAME,
) -> dict[str, Any]:
    canonical_size_linked_rows = int(linked_size_rows)
    total_rows = int(total_rows)
    linked_model_rows = int(linked_model_rows)
    linked_size_rows = int(linked_size_rows)
    retailer_count = int(retailer_count)
    canonical_size_linked_pct = link_pct(canonical_size_linked_rows, total_rows)
    return {
        "event": "inventory_link_health_snapshot",
        "service": service,
        "generated_at_utc": generated_at_utc or utc_timestamp(),
        "region": region,
        "total_rows": total_rows,
        "linked_model_rows": linked_model_rows,
        "linked_size_rows": linked_size_rows,
        "linked_model_pct": link_pct(linked_model_rows, total_rows),
        "linked_size_pct": link_pct(linked_size_rows, total_rows),
        "canonical_size_linked_rows": canonical_size_linked_rows,
        "canonical_size_linked_pct": canonical_size_linked_pct,
        "searchable_rows": canonical_size_linked_rows,
        "searchable_pct": canonical_size_linked_pct,
        "retailer_count": retailer_count,
    }


def build_retailer_payload(
    region: str,
    retailer_name: str,
    total_rows: int,
    linked_model_rows: int,
    linked_size_rows: int,
    generated_at_utc: str | None = None,
    service: str = SERVICE_NAME,
) -> dict[str, Any]:
    canonical_size_linked_rows = int(linked_size_rows)
    total_rows = int(total_rows)
    linked_model_rows = int(linked_model_rows)
    linked_size_rows = int(linked_size_rows)
    canonical_size_linked_pct = link_pct(canonical_size_linked_rows, total_rows)
    return {
        "event": "inventory_link_health_retailer",
        "service": service,
        "generated_at_utc": generated_at_utc or utc_timestamp(),
        "region": region,
        "retailer_name": retailer_name,
        "total_rows": total_rows,
        "linked_model_rows": linked_model_rows,
        "linked_size_rows": linked_size_rows,
        "linked_model_pct": link_pct(linked_model_rows, total_rows),
        "linked_size_pct": link_pct(linked_size_rows, total_rows),
        "canonical_size_linked_rows": canonical_size_linked_rows,
        "canonical_size_linked_pct": canonical_size_linked_pct,
        "searchable_rows": canonical_size_linked_rows,
        "searchable_pct": canonical_size_linked_pct,
    }


def _rows(query: str) -> list[Any]:
    return execute_with_retry(text(query))


def collect_inventory_link_health(
    generated_at_utc: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    generated_at_utc = generated_at_utc or utc_timestamp()
    snapshot_rows = _rows(SNAPSHOT_QUERY)
    retailer_rows = _rows(RETAILER_QUERY)

    snapshots = sorted(
        [
            build_snapshot_payload(
                region=str(_field(row, "RegionCode", "<NULL>")),
                total_rows=int(_field(row, "TotalRows", 0)),
                linked_model_rows=int(_field(row, "LinkedModelRows", 0)),
                linked_size_rows=int(_field(row, "LinkedSizeRows", 0)),
                retailer_count=int(_field(row, "RetailerCount", 0)),
                generated_at_utc=generated_at_utc,
            )
            for row in snapshot_rows
        ],
        key=lambda item: _region_sort_key(str(item["region"])),
    )

    retailers = sorted(
        [
            build_retailer_payload(
                region=str(_field(row, "RegionCode", "<NULL>")),
                retailer_name=str(_field(row, "RetailerName", "<unknown>")),
                total_rows=int(_field(row, "TotalRows", 0)),
                linked_model_rows=int(_field(row, "LinkedModelRows", 0)),
                linked_size_rows=int(_field(row, "LinkedSizeRows", 0)),
                generated_at_utc=generated_at_utc,
            )
            for row in retailer_rows
        ],
        key=lambda item: _retailer_sort_key(str(item["region"]), str(item["retailer_name"])),
    )
    return snapshots, retailers


def emit_inventory_link_health_report() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    snapshots, retailers = collect_inventory_link_health()
    for payload in [*snapshots, *retailers]:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), flush=True)
    return snapshots, retailers
