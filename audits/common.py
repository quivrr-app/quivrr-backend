from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
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
ROOT = Path(__file__).resolve().parents[1]
SCRIPT_OUTPUT_ROOT = ROOT / "scripts" / "output"
BRAND_OUTPUT_ROOT = ROOT / "scrapers" / "brands"

BRAND_SOURCE_FILES: dict[str, dict[str, Path]] = {
    "Album": {
        "catalogue": BRAND_OUTPUT_ROOT / "album" / "output" / "album_master_catalogue_clean.json",
        "report": BRAND_OUTPUT_ROOT / "album" / "output" / "album_master_catalogue_clean_report.json",
    },
    "Channel Islands": {
        "catalogue": BRAND_OUTPUT_ROOT / "channel_islands" / "output" / "ci_master_catalogue_clean.json",
        "report": BRAND_OUTPUT_ROOT / "channel_islands" / "output" / "ci_master_catalogue_clean_report.json",
        "expected_models": BRAND_OUTPUT_ROOT / "channel_islands" / "output" / "ci_canonical_model_links.json",
    },
    "Haydenshapes": {
        "catalogue": BRAND_OUTPUT_ROOT / "haydenshapes" / "output" / "haydenshapes_master_catalogue_clean.json",
        "report": BRAND_OUTPUT_ROOT / "haydenshapes" / "output" / "haydenshapes_master_catalogue_clean_report.json",
    },
    "JS Industries": {
        "catalogue": BRAND_OUTPUT_ROOT / "js" / "output" / "js_page_catalogue.json",
        "report": BRAND_OUTPUT_ROOT / "js" / "output" / "js_page_catalogue_report.json",
        "expected_models": BRAND_OUTPUT_ROOT / "js" / "js_canonical_models.json",
    },
    "Lost": {
        "catalogue": BRAND_OUTPUT_ROOT / "lost" / "output" / "lost_master_catalogue_clean.json",
        "report": BRAND_OUTPUT_ROOT / "lost" / "output" / "lost_master_catalogue_clean_report.json",
    },
    "Pyzel": {
        "catalogue": BRAND_OUTPUT_ROOT / "pyzel" / "output" / "pyzel_master_catalogue_clean.json",
        "report": BRAND_OUTPUT_ROOT / "pyzel" / "output" / "pyzel_master_catalogue_clean_report.json",
    },
}

GLOBAL_ALIAS_CANDIDATES: dict[str, dict[str, str]] = {
    "Album": {
        "Protoatypical": "ProtoAtypical",
    },
    "Channel Islands": {
        "Feb's Fish": "Feb's Fish",
        "Black and White": "Black/White",
        "FishBeard": "Fish Beard",
        "M-23": "M23",
        "Mikey Febs Fish": "Feb's Fish",
        "Mikey February's Fish": "Feb's Fish",
        "Mikey February Shorty": "Mikey February Shorty",
        "TPH Single": "Tri Plane Hull",
        "The Black Beauty": "Black Beauty",
        "The Water Hog": "Waterhog",
    },
    "Haydenshapes": {
        "Hypto Twin": "Hypto Krypto Twin",
        "Hypto Twin FF": "Hypto Krypto Twin",
        "Hypto Twin PU": "Hypto Krypto Twin",
    },
    "JS Industries": {
        "Big Horse Tier 1 & 2": "Big Horse",
        "Big Horse Tier 3": "Big Horse",
    },
    "Lost": {
        "California Twin": "Cali Twin",
        "Mini Driver": "Mini Driver (Re Issue)",
    },
}


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


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
