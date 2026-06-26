from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy import text

from market_intelligence.db import execute_with_retry


SUPPORTED_BRAND_ALIASES: dict[str, tuple[str, ...]] = {
    "Album": ("Album",),
    "Channel Islands": ("Channel Islands",),
    "Chemistry Surfboards": ("Chemistry Surfboards",),
    "Chilli": ("Chilli",),
    "Christenson": ("Christenson",),
    "DHD": ("DHD",),
    "DMS Surfboards": ("DMS Surfboards", "DMS"),
    "Firewire": ("Firewire",),
    "Haydenshapes": ("Haydenshapes",),
    "JS Industries": ("JS Industries",),
    "Lost": ("Lost",),
    "Misfit Shapes": ("Misfit Shapes", "Misfit"),
    "Pukas": ("Pukas",),
    "Pyzel": ("Pyzel",),
    "Rusty": ("Rusty",),
    "Sharp Eye": ("Sharp Eye", "SharpEye"),
    "Simon Anderson": ("Simon Anderson",),
}

SUPPORTED_BRANDS = tuple(SUPPORTED_BRAND_ALIASES.keys())
REGIONS = ("AU", "EU", "ID", "US")
AVAILABLE_STOCK_STATUSES = {
    "in stock",
    "instock",
    "in_stock",
    "available",
    "true",
}
ALBUM_EXPECTED_MODELS = (
    "Bom Dia",
    "CLS",
    "Darkness",
    "Delma",
    "Disaster",
    "Disorder",
    "Fascination",
    "Freewing",
    "Insanity",
    "Ledge",
    "Lightbender",
    "Lucent",
    "Moonstone",
    "Plasmic",
    "Protoatypical",
    "Sunstone",
    "Symphony",
    "The End",
    "Townsend",
    "Twinsman",
    "Twinsman AP",
    "Twinsman Mega",
    "Twinsman Pin",
    "VBSM",
    "Veebee",
    "Warp Twin",
    "Winzman",
)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text_value = str(value).strip().lower()
    text_value = text_value.replace("&", " and ")
    text_value = text_value.replace("’", "'").replace("‘", "'")
    text_value = re.sub(r"[^a-z0-9]+", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    return {
        key: getattr(row, key)
        for key in dir(row)
        if not key.startswith("_")
    }


def available_stock_status(value: Any) -> bool:
    if value is None:
        return True
    return normalize_text(value) in AVAILABLE_STOCK_STATUSES


def normalize_brand_name(value: Any) -> str:
    normal = normalize_text(value)
    for display_name, aliases in SUPPORTED_BRAND_ALIASES.items():
        if any(normal == normalize_text(alias) for alias in aliases):
            return display_name
    return str(value or "").strip()


def brand_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for display_name, aliases in SUPPORTED_BRAND_ALIASES.items():
        for alias in aliases:
            lookup[normalize_text(alias)] = display_name
    return lookup


def resolve_supported_brands() -> list[dict[str, Any]]:
    alias_values = sorted(
        {
            alias
            for aliases in SUPPORTED_BRAND_ALIASES.values()
            for alias in aliases
        }
    )
    placeholders = ", ".join(f":name_{idx}" for idx in range(len(alias_values)))
    params = {
        f"name_{idx}": alias
        for idx, alias in enumerate(alias_values)
    }
    rows = execute_with_retry(
        text(
            f"""
            SELECT BrandId, BrandName
            FROM dbo.Brands
            WHERE IsActive = 1
              AND BrandName IN ({placeholders})
            ORDER BY BrandName, BrandId
            """
        ),
        params,
    )
    alias_map = brand_alias_lookup()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        payload = row_to_dict(row)
        display_name = alias_map.get(normalize_text(payload.get("BrandName")), payload.get("BrandName"))
        grouped[display_name].append(payload)

    resolved = []
    for display_name in SUPPORTED_BRANDS:
        brand_rows = grouped.get(display_name, [])
        resolved.append(
            {
                "displayName": display_name,
                "brandIds": [int(item["BrandId"]) for item in brand_rows],
                "brandNames": [str(item["BrandName"]) for item in brand_rows],
                "primaryBrandId": int(brand_rows[0]["BrandId"]) if brand_rows else None,
            }
        )
    return resolved


def available_status_sql(column_name: str) -> str:
    return (
        f"{column_name} IS NULL OR "
        f"LOWER(LTRIM(RTRIM({column_name}))) IN ('in stock', 'instock', 'in_stock', 'available', 'true')"
    )


def load_table_columns(table_name: str) -> set[str]:
    rows = execute_with_retry(
        text(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = :table_name
            """
        ),
        {"table_name": table_name},
    )
    return {
        str(row_to_dict(row).get("COLUMN_NAME"))
        for row in rows
    }


def choose_timestamp_expression(
    table_alias: str,
    available_columns: set[str],
    *,
    candidates: tuple[str, ...] = ("UpdatedAtUtc", "UpdatedAt", "CreatedAtUtc", "CreatedAt"),
) -> str | None:
    usable = [
        f"{table_alias}.[{column_name}]"
        for column_name in candidates
        if column_name in available_columns
    ]
    if not usable:
        return None
    return f"COALESCE({', '.join(usable)})"


def format_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

