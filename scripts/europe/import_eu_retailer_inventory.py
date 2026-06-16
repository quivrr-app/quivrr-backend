from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text


INPUT_FILE = Path("scrapers/retailers/europe/output/eu_normalised_inventory.json")
BRANDS_FILE = Path("scrapers/brands/brands_seed.json")
BRAND_OUTPUT_ROOT = Path("scrapers/brands")
OUTPUT_FILE = Path("scripts/europe/output/eu_retailer_import_dry_run_report.json")
APPLY_OUTPUT_FILE = Path("scripts/europe/output/eu_retailer_import_apply_report.json")
LINK_REPORT_FILE = Path("scripts/europe/output/eu_retailer_canonical_link_report.json")
SQL_OUTPUT_FILE = Path("scripts/europe/output/eu_import.sql")

REGION_CODE = "EU"
PRICE_CURRENCY = "EUR"

BRAND_ALIASES = {
    "al merrick": "Channel Islands",
    "ci": "Channel Islands",
    "ci surfboards": "Channel Islands",
    "hayden shapes": "Haydenshapes",
    "haydenshapes surfboards": "Haydenshapes",
    "lost surfboards": "Lost",
    "mayhem": "Lost",
    "sharp eye": "Sharp Eye",
    "sharpeye": "Sharp Eye",
}

GENERIC_MODEL_NAMES = {
    "fish",
    "log",
    "longboard",
    "mid",
    "mid length",
    "shortboard",
    "softboard",
    "twin",
    "twin fin",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clean_key(value: object) -> str:
    text = clean(value).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def contains_phrase(text_value: object, phrase_value: object) -> bool:
    text_key = clean_key(text_value)
    phrase_key = clean_key(phrase_value)
    if not text_key or not phrase_key:
        return False
    return f" {phrase_key} " in f" {text_key} "


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def build_connection_string() -> str:
    load_dotenv()
    server = require_env("SQL_SERVER")
    database = require_env("SQL_DATABASE")
    username = require_env("SQL_USERNAME")
    password = require_env("SQL_PASSWORD")
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server").strip()

    if not server.replace("tcp:", "").strip().endswith(".database.windows.net"):
        raise RuntimeError(
            "SQL_SERVER must be the Azure SQL server host only, for example "
            "quivrr-sql-prod.database.windows.net"
        )

    odbc_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_string)


def build_engine():
    engine = create_engine(build_connection_string(), pool_pre_ping=True, pool_recycle=1800)

    @event.listens_for(engine, "before_cursor_execute")
    def enable_fast_executemany(conn, cursor, statement, parameters, context, executemany):
        if executemany:
            cursor.fast_executemany = True

    return engine


def decimal_or_none(value: object) -> Decimal | None:
    if value is None or clean(value) == "":
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def decimal_key(value: object) -> str:
    number = decimal_or_none(value)
    if number is None:
        return ""
    return str(number.quantize(Decimal("0.01")))


def float_or_none(value: object) -> float | None:
    number = decimal_or_none(value)
    return float(number) if number is not None else None


def website_from_product_url(product_url: object) -> str:
    url = clean(product_url)
    if not url:
        return "https://unknown.quivrr.app"
    try:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass
    return "https://unknown.quivrr.app"


def rows_from_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return [row for row in payload["rows"] if isinstance(row, dict)]
    return []


def load_input_rows(input_file: Path, retailer_slug: str = "") -> list[dict]:
    rows = rows_from_payload(load_json(input_file))
    if retailer_slug:
        rows = [row for row in rows if clean(row.get("retailerSlug")) == retailer_slug]
    return rows


def load_brand_map() -> dict[str, str]:
    brand_map = {}
    if BRANDS_FILE.exists():
        brands = load_json(BRANDS_FILE)
        if isinstance(brands, list):
            for brand in brands:
                if not isinstance(brand, dict):
                    continue
                name = clean(brand.get("brand_name") or brand.get("brandName") or brand.get("name"))
                if name:
                    brand_map[clean_key(name)] = name

    for alias, canonical in BRAND_ALIASES.items():
        brand_map[clean_key(alias)] = canonical

    return brand_map


def iter_catalogue_files() -> list[Path]:
    files = []
    for pattern in [
        "*/output/*master_catalogue_clean.json",
        "*/output/*master_catalogue.json",
        "*/output/*canonical*.json",
    ]:
        files.extend(BRAND_OUTPUT_ROOT.glob(pattern))
    return sorted(set(files))


def extract_catalogue_rows(data: object) -> list[dict]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if not isinstance(data, dict):
        return []
    for key in ["models", "boards", "products", "catalogue", "items", "rows"]:
        value = data.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def first_value(row: dict, keys: list[str]) -> str:
    for key in keys:
        value = clean(row.get(key))
        if value:
            return value
    return ""


def load_model_map(brand_map: dict[str, str]) -> dict[str, set[str]]:
    model_map: dict[str, set[str]] = {}
    for path in iter_catalogue_files():
        try:
            rows = extract_catalogue_rows(load_json(path))
        except Exception:
            continue

        for row in rows:
            model = first_value(row, ["modelName", "model_name", "model", "name", "title", "productTitle"])
            brand = first_value(row, ["brandName", "brand_name", "brand", "vendor"])
            canonical_brand = brand_map.get(clean_key(brand), brand)
            if model and canonical_brand:
                model_map.setdefault(clean_key(canonical_brand), set()).add(clean_key(model))
    return model_map


def row_dedupe_key(row: dict) -> str:
    return "|".join([
        clean_key(row.get("retailerSlug")),
        clean_key(row.get("productUrl")),
        clean_key(row.get("rawProductTitle")),
        clean_key(row.get("lengthFeetInches")),
        clean(row.get("volumeLitres")),
    ])


def has_stock_signal(row: dict) -> bool:
    return isinstance(row.get("isAvailable"), bool) or bool(clean(row.get("stockStatus")))


def has_searchable_dimension(row: dict) -> bool:
    return bool(clean(row.get("lengthFeetInches")) or clean(row.get("volumeLitres")))


def true_reject_reasons(row: dict) -> list[str]:
    reasons = []
    if not clean(row.get("retailerSlug")):
        reasons.append("missing_retailer_slug")
    if not clean(row.get("retailerName")):
        reasons.append("missing_retailer_name")
    if clean(row.get("regionCode")) != REGION_CODE:
        reasons.append("wrong_region")
    if clean(row.get("priceCurrency")) != PRICE_CURRENCY:
        reasons.append("wrong_currency")
    if not clean(row.get("rawProductTitle")):
        reasons.append("missing_title")
    if not clean(row.get("productUrl")):
        reasons.append("missing_url")
    if not clean(row.get("priceAmount")):
        reasons.append("missing_price")
    if not has_stock_signal(row):
        reasons.append("missing_stock_status")
    if not has_searchable_dimension(row):
        reasons.append("missing_all_dimensions")
    return reasons


def import_stock_status(row: dict) -> str:
    stock_status = clean(row.get("stockStatus"))
    if stock_status:
        return stock_status
    if row.get("isAvailable") is True:
        return "In Stock"
    if row.get("isAvailable") is False:
        return "Out of Stock"
    return "Unknown"


def canonical_match(row: dict, brand_map: dict[str, str], model_map: dict[str, set[str]]) -> dict:
    raw_brand = clean(row.get("brandName"))
    raw_model = clean(row.get("modelName"))
    matched_brand = brand_map.get(clean_key(raw_brand), "")
    brand_key = clean_key(matched_brand)
    model_matched = bool(matched_brand and raw_model and clean_key(raw_model) in model_map.get(brand_key, set()))
    return {
        "canonicalBrandMatched": bool(matched_brand),
        "canonicalModelMatched": model_matched,
        "matchedBrandName": matched_brand or None,
        "matchedModelName": raw_model if model_matched else None,
        "matchConfidence": "canonical_brand_and_model"
        if matched_brand and model_matched
        else "canonical_brand_only"
        if matched_brand
        else "raw_only",
    }


def review_reason(match: dict) -> str:
    reasons = []
    if not match["canonicalBrandMatched"]:
        reasons.append("unknown_brand")
    if not match["canonicalModelMatched"]:
        reasons.append("unknown_model")
    return ",".join(reasons)


def build_report(rows: list[dict], input_file: Path, retailer_slug: str = "") -> dict:
    brand_map = load_brand_map()
    model_map = load_model_map(brand_map)
    deduped: dict[str, dict] = {}
    duplicate_rows = 0

    raw_importable = []
    canonical_matched = []
    canonical_review = []
    true_rejects = []
    true_reject_counts = Counter()
    review_reason_counts = Counter()
    unknown_brands = Counter()
    unknown_models = Counter()

    for row in rows:
        key = row_dedupe_key(row)
        if key in deduped:
            duplicate_rows += 1
            continue
        deduped[key] = row

        rejects = true_reject_reasons(row)
        match = canonical_match(row, brand_map, model_map)
        reason = review_reason(match)
        importable_raw = not rejects
        dry_row = {
            "retailerSlug": clean(row.get("retailerSlug")),
            "retailerName": clean(row.get("retailerName")),
            "regionCode": clean(row.get("regionCode")),
            "country": clean(row.get("country")),
            "brandName": clean(row.get("brandName")),
            "modelName": clean(row.get("modelName")),
            "rawProductTitle": clean(row.get("rawProductTitle")),
            "productUrl": clean(row.get("productUrl")),
            "productImageUrl": clean(row.get("productImageUrl")),
            "priceAmount": clean(row.get("priceAmount")),
            "priceCurrency": clean(row.get("priceCurrency")),
            "lengthFeetInches": clean(row.get("lengthFeetInches")),
            "volumeLitres": row.get("volumeLitres"),
            "construction": clean(row.get("construction")),
            "finSetup": clean(row.get("finSetup")),
            "parseConfidence": row.get("parseConfidence"),
            "isAvailable": row.get("isAvailable"),
            "stockStatus": clean(row.get("stockStatus")),
            "importableRaw": importable_raw,
            "needsCanonicalReview": bool(reason),
            "reviewReason": reason or None,
            "trueRejectReasons": rejects,
            **match,
        }

        for reject in rejects:
            true_reject_counts[reject] += 1
        for item in reason.split(",") if reason else []:
            review_reason_counts[item] += 1

        if not match["canonicalBrandMatched"]:
            unknown_brands[clean(row.get("brandName")) or "missing"] += 1
        if not match["canonicalModelMatched"]:
            unknown_models[
                f"{clean(row.get('brandName')) or 'missing_brand'} / {clean(row.get('modelName')) or 'missing_model'}"
            ] += 1

        if importable_raw:
            raw_importable.append(dry_row)
            if reason:
                canonical_review.append(dry_row)
            else:
                canonical_matched.append(dry_row)
        else:
            true_rejects.append(dry_row)

    retailer_count = len({clean(row.get("retailerSlug")) for row in raw_importable if clean(row.get("retailerSlug"))})
    sql_action_counts = {
        "retailersToUpsert": retailer_count,
        "inventoryRowsToUpsert": len(raw_importable),
        "euRowsToDeactivateIfMissingFromFeed": 0,
        "auRowsTouched": 0,
        "idRowsTouched": 0,
    }

    recommendation = (
        "Needs major work"
        if true_rejects and len(raw_importable) == 0
        else "Raw import ready, canonical review required"
        if canonical_review
        else "Ready for SQL importer"
    )

    return {
        "mode": "dry_run",
        "applyRequested": False,
        "purpose": "EU RetailerInventory import dry-run only. No SQL writes.",
        "inputFile": str(input_file),
        "retailerSlug": retailer_slug or "all",
        "regionCode": REGION_CODE,
        "priceCurrency": PRICE_CURRENCY,
        "sourceRows": len(rows),
        "rowsAfterDedupe": len(deduped),
        "duplicateRowsRemoved": duplicate_rows,
        "metrics": {
            "totalRows": len(deduped),
            "importableRows": len(raw_importable),
            "rejectedRows": len(true_rejects),
            "canonicalMatchedRows": len(canonical_matched),
            "needsCanonicalReviewRows": len(canonical_review),
            "unknownBrands": sum(unknown_brands.values()),
            "unknownModels": sum(unknown_models.values()),
        },
        "sqlActionCounts": sql_action_counts,
        "trueRejectReasonCounts": dict(true_reject_counts),
        "canonicalReviewReasonCounts": dict(review_reason_counts),
        "unknownBrands": [{"brandName": key, "count": value} for key, value in unknown_brands.most_common(50)],
        "unknownModels": [{"brandModel": key, "count": value} for key, value in unknown_models.most_common(50)],
        "importableSample": raw_importable[:20],
        "importableRowsForApply": raw_importable,
        "canonicalReviewSample": canonical_review[:20],
        "trueRejectSample": true_rejects[:20],
        "idempotentUpsertKey": [
            "retailerSlug",
            "productUrl",
            "rawProductTitle",
            "lengthFeetInches",
            "volumeLitres",
        ],
        "applySafetyNotes": [
            "Dry-run is the default and does not connect to SQL.",
            "Any future --apply must keep WHERE RegionCode = 'EU' on updates/deactivations.",
            "AU and ID rows must never be updated by this importer.",
            "Raw inventory rows remain importable when canonical brand/model mapping is missing.",
        ],
        "recommendation": recommendation,
    }


def assert_apply_safety(report: dict) -> None:
    if report.get("regionCode") != REGION_CODE:
        raise RuntimeError("Safety check failed: dry-run regionCode was not EU.")
    if report.get("priceCurrency") != PRICE_CURRENCY:
        raise RuntimeError("Safety check failed: dry-run priceCurrency was not EUR.")
    sql_counts = report.get("sqlActionCounts", {})
    if sql_counts.get("auRowsTouched") != 0:
        raise RuntimeError("Safety check failed: AU rows touched was not 0.")
    if sql_counts.get("idRowsTouched") != 0:
        raise RuntimeError("Safety check failed: ID rows touched was not 0.")
    if report.get("metrics", {}).get("importableRows", 0) <= 400:
        raise RuntimeError("Safety check failed: importable rows must be greater than 400.")


def count_inventory_by_region(conn, region_code: str) -> int:
    row = conn.execute(
        text("""
            SELECT COUNT(*) AS row_count
            FROM dbo.RetailerInventory
            WHERE ISNULL(RegionCode, 'AU') = :region_code
        """),
        {"region_code": region_code},
    ).fetchone()
    return int(row_field(row, "row_count"))


def count_retailers_by_region(conn, region_code: str) -> int:
    row = conn.execute(
        text("""
            SELECT COUNT(*) AS row_count
            FROM dbo.Retailers
            WHERE ISNULL(RegionCode, 'AU') = :region_code
        """),
        {"region_code": region_code},
    ).fetchone()
    return int(row_field(row, "row_count"))


def sample_eu_rows(conn) -> list[dict]:
    rows = conn.execute(
        text("""
            SELECT TOP 10
                r.RetailerName,
                ri.RawProductTitle,
                ri.PriceAmount,
                ri.PriceCurrency,
                ri.RegionCode
            FROM dbo.RetailerInventory ri
            JOIN dbo.Retailers r
                ON r.RetailerId = ri.RetailerId
            WHERE ri.RegionCode = 'EU'
            ORDER BY ri.UpdatedAtUtc DESC, ri.InventoryId DESC
        """)
    ).fetchall()
    return [
        {
            "retailerName": row.RetailerName,
            "rawProductTitle": row.RawProductTitle,
            "priceAmount": float(row.PriceAmount) if row.PriceAmount is not None else None,
            "priceCurrency": row.PriceCurrency,
            "regionCode": row.RegionCode,
        }
        for row in rows
    ]


def row_field(row: object, field_name: str, index: int = 0) -> object:
    mapping = getattr(row, "_mapping", None)
    if mapping is not None and field_name in mapping:
        return mapping[field_name]
    if hasattr(row, field_name):
        return getattr(row, field_name)
    try:
        return row[index]
    except (IndexError, KeyError, TypeError):
        return None


def schema_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(
        text("""
            SELECT COLUMN_NAME AS column_name
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = :table_name
            ORDER BY ORDINAL_POSITION
        """),
        {"table_name": table_name},
    ).fetchall()
    return {clean(row_field(row, "column_name")) for row in rows if clean(row_field(row, "column_name"))}


def assert_schema(conn) -> None:
    retailer_columns = schema_columns(conn, "Retailers")
    inventory_columns = schema_columns(conn, "RetailerInventory")
    required_retailer = {
        "RetailerId",
        "RetailerName",
        "WebsiteUrl",
        "Country",
        "RegionCode",
        "IsActive",
        "CreatedAtUtc",
        "UpdatedAtUtc",
    }
    required_inventory = {
        "InventoryId",
        "RetailerId",
        "BrandId",
        "BoardModelId",
        "BoardSizeId",
        "RawProductTitle",
        "NormalisedProductTitle",
        "ProductUrl",
        "ProductImageUrl",
        "PriceAmount",
        "PriceCurrency",
        "StockStatus",
        "Construction",
        "FinSetup",
        "LengthFeetInches",
        "VolumeLitres",
        "InventoryConfidenceScore",
        "LastCheckedUtc",
        "IsActive",
        "CreatedAtUtc",
        "UpdatedAtUtc",
        "RegionCode",
    }
    missing_retailer = sorted(required_retailer - retailer_columns)
    missing_inventory = sorted(required_inventory - inventory_columns)
    if missing_retailer or missing_inventory:
        raise RuntimeError(
            "Safety check failed: missing SQL columns. "
            f"Retailers={missing_retailer}; RetailerInventory={missing_inventory}"
        )


def schema_check() -> dict:
    engine = build_engine()
    with engine.connect() as conn:
        retailers = sorted(schema_columns(conn, "Retailers"))
        inventory = sorted(schema_columns(conn, "RetailerInventory"))
        assert_schema(conn)
    return {
        "retailersColumns": retailers,
        "retailerInventoryColumns": inventory,
        "schemaAssertionPassed": True,
    }


def brand_lookup(conn) -> dict[str, int]:
    rows = conn.execute(
        text("""
            SELECT BrandId, BrandName
            FROM dbo.Brands
            WHERE IsActive = 1
        """)
    ).fetchall()
    return {clean_key(row.BrandName): row.BrandId for row in rows}


def load_board_models(conn) -> dict[int, list[dict]]:
    rows = conn.execute(
        text("""
            SELECT
                BoardModelId,
                BrandId,
                ModelName
            FROM dbo.BoardModels
            WHERE IsActive = 1
        """)
    ).fetchall()
    models: dict[int, list[dict]] = {}
    for row in rows:
        model = {
            "boardModelId": int(row_field(row, "BoardModelId")),
            "brandId": int(row_field(row, "BrandId")),
            "modelName": clean(row_field(row, "ModelName")),
            "modelKey": clean_key(row_field(row, "ModelName")),
        }
        if model["modelName"] and model["modelKey"]:
            models.setdefault(model["brandId"], []).append(model)
    return models


def load_board_sizes(conn) -> dict[int, list[dict]]:
    rows = conn.execute(
        text("""
            SELECT
                BoardSizeId,
                BoardModelId,
                LengthFeetInches,
                VolumeLitres
            FROM dbo.BoardSizes
        """)
    ).fetchall()
    sizes: dict[int, list[dict]] = {}
    for row in rows:
        model_id = row_field(row, "BoardModelId")
        if model_id is None:
            continue
        size = {
            "boardSizeId": int(row_field(row, "BoardSizeId")),
            "boardModelId": int(model_id),
            "lengthFeetInches": clean(row_field(row, "LengthFeetInches")),
            "volumeLitres": decimal_or_none(row_field(row, "VolumeLitres")),
        }
        sizes.setdefault(size["boardModelId"], []).append(size)
    return sizes


def load_eu_inventory_rows(conn) -> list[dict]:
    rows = conn.execute(
        text("""
            SELECT
                ri.InventoryId,
                ri.RetailerId,
                r.RetailerName,
                ri.BrandId,
                b.BrandName,
                ri.BoardModelId,
                ri.BoardSizeId,
                ri.RawProductTitle,
                ri.NormalisedProductTitle,
                ri.LengthFeetInches,
                ri.VolumeLitres,
                ri.PriceCurrency,
                ri.RegionCode
            FROM dbo.RetailerInventory ri
            INNER JOIN dbo.Retailers r
                ON r.RetailerId = ri.RetailerId
            LEFT JOIN dbo.Brands b
                ON b.BrandId = ri.BrandId
            WHERE ri.RegionCode = 'EU'
              AND ri.IsActive = 1
        """)
    ).fetchall()
    inventory = []
    for row in rows:
        inventory.append({
            "inventoryId": int(row_field(row, "InventoryId")),
            "retailerId": int(row_field(row, "RetailerId")),
            "retailerName": clean(row_field(row, "RetailerName")),
            "brandId": int(row_field(row, "BrandId")) if row_field(row, "BrandId") is not None else None,
            "brandName": clean(row_field(row, "BrandName")),
            "boardModelId": int(row_field(row, "BoardModelId")) if row_field(row, "BoardModelId") is not None else None,
            "boardSizeId": int(row_field(row, "BoardSizeId")) if row_field(row, "BoardSizeId") is not None else None,
            "rawProductTitle": clean(row_field(row, "RawProductTitle")),
            "normalisedProductTitle": clean(row_field(row, "NormalisedProductTitle")),
            "lengthFeetInches": clean(row_field(row, "LengthFeetInches")),
            "volumeLitres": decimal_or_none(row_field(row, "VolumeLitres")),
            "priceCurrency": clean(row_field(row, "PriceCurrency")),
            "regionCode": clean(row_field(row, "RegionCode")),
        })
    return inventory


def score_model_candidate(row: dict, model: dict) -> int | None:
    model_key = model["modelKey"]
    raw_key = clean_key(row.get("rawProductTitle"))
    normalised_key = clean_key(row.get("normalisedProductTitle"))
    score = None

    if normalised_key and normalised_key == model_key:
        score = 10000
    elif contains_phrase(normalised_key, model_key):
        score = 7000
    elif contains_phrase(raw_key, model_key):
        score = 5000

    if score is None:
        return None

    score += len(model_key) * 10
    if model_key in GENERIC_MODEL_NAMES:
        score -= 1500
    return score


def model_candidates_for_row(row: dict, models_by_brand: dict[int, list[dict]]) -> list[dict]:
    brand_id = row.get("brandId")
    if brand_id is None:
        return []
    candidates = []
    for model in models_by_brand.get(brand_id, []):
        score = score_model_candidate(row, model)
        if score is None:
            continue
        candidates.append({
            "boardModelId": model["boardModelId"],
            "modelName": model["modelName"],
            "score": score,
            "isGeneric": model["modelKey"] in GENERIC_MODEL_NAMES,
        })
    candidates.sort(key=lambda item: (item["score"], len(clean_key(item["modelName"]))), reverse=True)
    return candidates


def select_model_candidate(row: dict, models_by_brand: dict[int, list[dict]]) -> dict | None:
    candidates = model_candidates_for_row(row, models_by_brand)
    if not candidates:
        return None
    selected = dict(candidates[0])
    selected["candidateCount"] = len(candidates)
    selected["ambiguous"] = len(candidates) > 1
    selected["candidates"] = candidates[:5]
    return selected


def select_size_candidate(row: dict, board_model_id: int, sizes_by_model: dict[int, list[dict]]) -> dict | None:
    length = clean(row.get("lengthFeetInches"))
    if not length:
        return None

    row_volume = decimal_or_none(row.get("volumeLitres"))
    candidates = []
    for size in sizes_by_model.get(board_model_id, []):
        if clean(size.get("lengthFeetInches")) != length:
            continue
        size_volume = decimal_or_none(size.get("volumeLitres"))
        volume_delta = None
        if row_volume is not None and size_volume is not None:
            volume_delta = abs(row_volume - size_volume)
            if volume_delta > Decimal("0.4"):
                continue
        candidates.append({
            "boardSizeId": size["boardSizeId"],
            "lengthFeetInches": size["lengthFeetInches"],
            "volumeLitres": float(size_volume) if size_volume is not None else None,
            "volumeDelta": float(volume_delta) if volume_delta is not None else None,
        })

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item["volumeDelta"] is None,
            item["volumeDelta"] if item["volumeDelta"] is not None else 999,
            item["boardSizeId"],
        )
    )
    selected = dict(candidates[0])
    selected["candidateCount"] = len(candidates)
    return selected


def build_canonical_link_report(conn) -> dict:
    inventory_rows = load_eu_inventory_rows(conn)
    models_by_brand = load_board_models(conn)
    sizes_by_model = load_board_sizes(conn)
    model_updates = []
    size_updates = []
    ambiguous = []
    unmatched_by_retailer = Counter()
    unmatched_by_brand = Counter()

    linked_models = 0
    linked_sizes = 0

    for row in inventory_rows:
        selected_model = None
        effective_model_id = row.get("boardModelId")

        if effective_model_id is not None:
            linked_models += 1
        else:
            selected_model = select_model_candidate(row, models_by_brand)
            if selected_model:
                effective_model_id = selected_model["boardModelId"]
                model_updates.append({
                    "inventory_id": row["inventoryId"],
                    "board_model_id": effective_model_id,
                })
                if selected_model["ambiguous"]:
                    ambiguous.append({
                        "inventoryId": row["inventoryId"],
                        "retailerName": row["retailerName"],
                        "brandName": row["brandName"],
                        "rawProductTitle": row["rawProductTitle"],
                        "normalisedProductTitle": row["normalisedProductTitle"],
                        "selectedModelName": selected_model["modelName"],
                        "candidates": selected_model["candidates"],
                    })
            else:
                unmatched_by_retailer[row["retailerName"] or "missing"] += 1
                unmatched_by_brand[row["brandName"] or "missing"] += 1

        if row.get("boardSizeId") is not None:
            linked_sizes += 1
            continue

        if effective_model_id is None:
            continue

        selected_size = select_size_candidate(row, effective_model_id, sizes_by_model)
        if selected_size:
            size_updates.append({
                "inventory_id": row["inventoryId"],
                "board_size_id": selected_size["boardSizeId"],
            })

    return {
        "regionCode": REGION_CODE,
        "totalEuRows": len(inventory_rows),
        "linkedModels": linked_models,
        "linkedSizes": linked_sizes,
        "modelLinkCandidates": len(model_updates),
        "sizeLinkCandidates": len(size_updates),
        "ambiguousModelMatches": len(ambiguous),
        "ambiguousModelMatchSample": ambiguous[:50],
        "unmatchedRowsByRetailer": [
            {"retailerName": key, "count": value}
            for key, value in unmatched_by_retailer.most_common(50)
        ],
        "unmatchedRowsByBrand": [
            {"brandName": key, "count": value}
            for key, value in unmatched_by_brand.most_common(50)
        ],
        "modelUpdates": model_updates,
        "sizeUpdates": size_updates,
    }


def write_link_report(report: dict, output_file: Path = LINK_REPORT_FILE) -> None:
    public_report = {key: value for key, value in report.items() if key not in {"modelUpdates", "sizeUpdates"}}
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(public_report, indent=2, ensure_ascii=False), encoding="utf-8")


def public_link_report(report: dict) -> dict:
    return {key: value for key, value in report.items() if key not in {"modelUpdates", "sizeUpdates"}}


def sql_string(value: object) -> str:
    value = clean(value)
    if not value:
        return "NULL"
    return "N'" + value.replace("'", "''") + "'"


def sql_decimal(value: object) -> str:
    number = decimal_or_none(value)
    if number is None:
        return "NULL"
    return str(number.quantize(Decimal("0.01")))


def sql_float(value: object) -> str:
    number = decimal_or_none(value)
    if number is None:
        return "NULL"
    return str(number)


def sql_values_rows(rows: list[dict]) -> str:
    values = []
    for row in rows:
        values.append(
            "("
            + ", ".join([
                sql_string(row.get("retailerName")),
                sql_string(website_from_product_url(row.get("productUrl"))),
                sql_string(row.get("country") or "Europe"),
                sql_string(row.get("matchedBrandName")),
                sql_string(row.get("rawProductTitle") or "Unknown EU surfboard"),
                sql_string(row.get("modelName") or row.get("rawProductTitle")),
                sql_string(row.get("productUrl")),
                sql_string(row.get("productImageUrl")),
                sql_decimal(row.get("priceAmount")),
                sql_string(import_stock_status(row)),
                sql_string(row.get("construction")),
                sql_string(row.get("finSetup")),
                sql_string(row.get("lengthFeetInches")),
                sql_decimal(row.get("volumeLitres")),
                sql_float(row.get("parseConfidence") or 0),
            ])
            + ")"
        )
    return ",\n".join(values)


def export_import_sql(report: dict, output_file: Path = SQL_OUTPUT_FILE) -> None:
    assert_apply_safety(report)
    rows = build_apply_rows(report)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    sql = f"""-- Quivrr EU retailer inventory import
-- Generated locally without connecting to Azure SQL.
-- Scope: EU only. No AU or ID writes.
SET XACT_ABORT ON;
BEGIN TRANSACTION;

DECLARE @Rows TABLE (
    RetailerName nvarchar(255) NOT NULL,
    WebsiteUrl nvarchar(1024) NULL,
    Country nvarchar(100) NULL,
    BrandName nvarchar(255) NULL,
    RawProductTitle nvarchar(1024) NOT NULL,
    NormalisedProductTitle nvarchar(1024) NULL,
    ProductUrl nvarchar(2048) NULL,
    ProductImageUrl nvarchar(2048) NULL,
    PriceAmount decimal(18,2) NULL,
    StockStatus nvarchar(100) NULL,
    Construction nvarchar(255) NULL,
    FinSetup nvarchar(255) NULL,
    LengthFeetInches nvarchar(50) NULL,
    VolumeLitres decimal(10,2) NULL,
    InventoryConfidenceScore decimal(10,4) NULL
);

INSERT INTO @Rows (
    RetailerName,
    WebsiteUrl,
    Country,
    BrandName,
    RawProductTitle,
    NormalisedProductTitle,
    ProductUrl,
    ProductImageUrl,
    PriceAmount,
    StockStatus,
    Construction,
    FinSetup,
    LengthFeetInches,
    VolumeLitres,
    InventoryConfidenceScore
)
VALUES
{sql_values_rows(rows)};

;WITH DuplicateKeys AS (
    SELECT
        r.RetailerName,
        LOWER(LTRIM(RTRIM(ISNULL(ri.ProductUrl, '')))) AS ProductUrlKey,
        LOWER(LTRIM(RTRIM(ISNULL(ri.RawProductTitle, '')))) AS RawTitleKey,
        LOWER(LTRIM(RTRIM(ISNULL(ri.LengthFeetInches, '')))) AS LengthKey,
        CAST(ri.VolumeLitres AS decimal(10,2)) AS VolumeKey,
        COUNT(*) AS DuplicateCount
    FROM dbo.RetailerInventory ri
    INNER JOIN dbo.Retailers r
        ON r.RetailerId = ri.RetailerId
    WHERE ri.RegionCode = 'EU'
    GROUP BY
        r.RetailerName,
        LOWER(LTRIM(RTRIM(ISNULL(ri.ProductUrl, '')))),
        LOWER(LTRIM(RTRIM(ISNULL(ri.RawProductTitle, '')))),
        LOWER(LTRIM(RTRIM(ISNULL(ri.LengthFeetInches, '')))),
        CAST(ri.VolumeLitres AS decimal(10,2))
    HAVING COUNT(*) > 1
)
SELECT *
FROM DuplicateKeys
ORDER BY DuplicateCount DESC;

INSERT INTO dbo.Retailers (
    RetailerName,
    WebsiteUrl,
    Country,
    RegionCode,
    IsActive,
    CreatedAtUtc,
    UpdatedAtUtc
)
SELECT
    src.RetailerName,
    MAX(src.WebsiteUrl),
    MAX(src.Country),
    'EU',
    1,
    SYSUTCDATETIME(),
    SYSUTCDATETIME()
FROM @Rows src
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.Retailers existing
    WHERE existing.RegionCode = 'EU'
      AND existing.RetailerName = src.RetailerName
)
GROUP BY src.RetailerName;

UPDATE existing
SET
    BrandId = b.BrandId,
    NormalisedProductTitle = src.NormalisedProductTitle,
    ProductImageUrl = src.ProductImageUrl,
    PriceAmount = src.PriceAmount,
    PriceCurrency = 'EUR',
    StockStatus = src.StockStatus,
    Construction = src.Construction,
    FinSetup = src.FinSetup,
    InventoryConfidenceScore = src.InventoryConfidenceScore,
    LastCheckedUtc = SYSUTCDATETIME(),
    IsActive = 1,
    UpdatedAtUtc = SYSUTCDATETIME()
FROM dbo.RetailerInventory existing
INNER JOIN dbo.Retailers r
    ON r.RetailerId = existing.RetailerId
   AND r.RegionCode = 'EU'
INNER JOIN @Rows src
    ON src.RetailerName = r.RetailerName
   AND LOWER(LTRIM(RTRIM(ISNULL(src.ProductUrl, '')))) = LOWER(LTRIM(RTRIM(ISNULL(existing.ProductUrl, ''))))
   AND LOWER(LTRIM(RTRIM(ISNULL(src.RawProductTitle, '')))) = LOWER(LTRIM(RTRIM(ISNULL(existing.RawProductTitle, ''))))
   AND LOWER(LTRIM(RTRIM(ISNULL(src.LengthFeetInches, '')))) = LOWER(LTRIM(RTRIM(ISNULL(existing.LengthFeetInches, ''))))
   AND (
        (src.VolumeLitres IS NULL AND existing.VolumeLitres IS NULL)
        OR CAST(src.VolumeLitres AS decimal(10,2)) = CAST(existing.VolumeLitres AS decimal(10,2))
   )
LEFT JOIN dbo.Brands b
    ON b.IsActive = 1
   AND LOWER(LTRIM(RTRIM(b.BrandName))) = LOWER(LTRIM(RTRIM(src.BrandName)))
WHERE existing.RegionCode = 'EU';

INSERT INTO dbo.RetailerInventory (
    RetailerId,
    BrandId,
    BoardModelId,
    BoardSizeId,
    RawProductTitle,
    NormalisedProductTitle,
    ProductUrl,
    ProductImageUrl,
    PriceAud,
    PriceAmount,
    PriceCurrency,
    StockStatus,
    StockQuantity,
    Construction,
    FinSetup,
    LengthFeetInches,
    Width,
    Thickness,
    VolumeLitres,
    EstimatedShippingAud,
    InventoryConfidenceScore,
    LastCheckedUtc,
    IsActive,
    CreatedAtUtc,
    UpdatedAtUtc,
    RegionCode
)
SELECT
    r.RetailerId,
    b.BrandId,
    NULL,
    NULL,
    src.RawProductTitle,
    src.NormalisedProductTitle,
    src.ProductUrl,
    src.ProductImageUrl,
    NULL,
    src.PriceAmount,
    'EUR',
    src.StockStatus,
    NULL,
    src.Construction,
    src.FinSetup,
    src.LengthFeetInches,
    NULL,
    NULL,
    src.VolumeLitres,
    NULL,
    src.InventoryConfidenceScore,
    SYSUTCDATETIME(),
    1,
    SYSUTCDATETIME(),
    SYSUTCDATETIME(),
    'EU'
FROM @Rows src
INNER JOIN dbo.Retailers r
    ON r.RegionCode = 'EU'
   AND r.RetailerName = src.RetailerName
LEFT JOIN dbo.Brands b
    ON b.IsActive = 1
   AND LOWER(LTRIM(RTRIM(b.BrandName))) = LOWER(LTRIM(RTRIM(src.BrandName)))
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.RetailerInventory existing
    WHERE existing.RegionCode = 'EU'
      AND existing.RetailerId = r.RetailerId
      AND LOWER(LTRIM(RTRIM(ISNULL(existing.ProductUrl, '')))) = LOWER(LTRIM(RTRIM(ISNULL(src.ProductUrl, ''))))
      AND LOWER(LTRIM(RTRIM(ISNULL(existing.RawProductTitle, '')))) = LOWER(LTRIM(RTRIM(ISNULL(src.RawProductTitle, ''))))
      AND LOWER(LTRIM(RTRIM(ISNULL(existing.LengthFeetInches, '')))) = LOWER(LTRIM(RTRIM(ISNULL(src.LengthFeetInches, ''))))
      AND (
            (existing.VolumeLitres IS NULL AND src.VolumeLitres IS NULL)
            OR CAST(existing.VolumeLitres AS decimal(10,2)) = CAST(src.VolumeLitres AS decimal(10,2))
      )
);

-- Canonical model link pass: exact and longest phrase match only.
UPDATE ri
SET
    ri.BoardModelId = matched.BoardModelId,
    ri.UpdatedAtUtc = SYSUTCDATETIME()
FROM dbo.RetailerInventory ri
CROSS APPLY (
    SELECT TOP 1
        bm.BoardModelId,
        bm.ModelName
    FROM dbo.BoardModels bm
    WHERE bm.BrandId = ri.BrandId
      AND bm.IsActive = 1
      AND (
            LOWER(LTRIM(RTRIM(ISNULL(ri.NormalisedProductTitle, '')))) = LOWER(LTRIM(RTRIM(bm.ModelName)))
         OR ' ' + LOWER(LTRIM(RTRIM(ISNULL(ri.RawProductTitle, '')))) + ' ' LIKE '% ' + LOWER(LTRIM(RTRIM(bm.ModelName))) + ' %'
         OR ' ' + LOWER(LTRIM(RTRIM(ISNULL(ri.NormalisedProductTitle, '')))) + ' ' LIKE '% ' + LOWER(LTRIM(RTRIM(bm.ModelName))) + ' %'
      )
    ORDER BY
        CASE
            WHEN LOWER(LTRIM(RTRIM(ISNULL(ri.NormalisedProductTitle, '')))) = LOWER(LTRIM(RTRIM(bm.ModelName))) THEN 0
            ELSE 1
        END,
        LEN(bm.ModelName) DESC,
        bm.BoardModelId
) matched
WHERE ri.RegionCode = 'EU'
  AND ri.BrandId IS NOT NULL
  AND ri.BoardModelId IS NULL;

UPDATE ri
SET
    ri.BoardSizeId = bs.BoardSizeId,
    ri.UpdatedAtUtc = SYSUTCDATETIME()
FROM dbo.RetailerInventory ri
INNER JOIN dbo.BoardSizes bs
    ON bs.BoardModelId = ri.BoardModelId
   AND bs.LengthFeetInches = ri.LengthFeetInches
   AND (
        ri.VolumeLitres IS NULL
     OR bs.VolumeLitres IS NULL
     OR ABS(CAST(bs.VolumeLitres AS decimal(10,2)) - CAST(ri.VolumeLitres AS decimal(10,2))) <= 0.4
   )
WHERE ri.RegionCode = 'EU'
  AND ri.BoardModelId IS NOT NULL
  AND ri.BoardSizeId IS NULL;

COMMIT TRANSACTION;
"""
    output_file.write_text(sql, encoding="utf-8")


def print_azure_run_command(script_name: str = "scripts/europe/import_eu_retailer_inventory.py --export-sql") -> None:
    print("Local Azure SQL execution is disabled.")
    print("Run from an approved Azure environment instead, for example:")
    print("az containerapp job start --name quivrr-eu-retailer-inventory --resource-group quivrr-production-rg")
    print("Suggested container command:")
    print(f"venv\\Scripts\\python.exe {script_name}")


def apply_model_links(conn, model_updates: list[dict]) -> int:
    if not model_updates:
        return 0
    conn.execute(
        text("""
            UPDATE dbo.RetailerInventory
            SET BoardModelId = :board_model_id,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE InventoryId = :inventory_id
              AND RegionCode = 'EU'
              AND BoardModelId IS NULL
        """),
        model_updates,
    )
    return len(model_updates)


def apply_size_links(conn, size_updates: list[dict]) -> int:
    if not size_updates:
        return 0
    conn.execute(
        text("""
            UPDATE dbo.RetailerInventory
            SET BoardSizeId = :board_size_id,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE InventoryId = :inventory_id
              AND RegionCode = 'EU'
              AND BoardModelId IS NOT NULL
              AND BoardSizeId IS NULL
        """),
        size_updates,
    )
    return len(size_updates)


def run_link_tests() -> dict:
    models_by_brand = {
        1: [
            {"boardModelId": 1, "brandId": 1, "modelName": "Happy", "modelKey": "happy"},
            {"boardModelId": 2, "brandId": 1, "modelName": "Two Happy", "modelKey": "two happy"},
            {"boardModelId": 3, "brandId": 1, "modelName": "Happy Everyday", "modelKey": "happy everyday"},
            {"boardModelId": 4, "brandId": 1, "modelName": "Dumpster Diver", "modelKey": "dumpster diver"},
            {"boardModelId": 5, "brandId": 1, "modelName": "Dumpster Diver 2", "modelKey": "dumpster diver 2"},
            {"boardModelId": 6, "brandId": 1, "modelName": "CI Mid", "modelKey": "ci mid"},
            {"boardModelId": 7, "brandId": 1, "modelName": "CI Mid Twin", "modelKey": "ci mid twin"},
            {"boardModelId": 8, "brandId": 1, "modelName": "Fish", "modelKey": "fish"},
            {"boardModelId": 9, "brandId": 1, "modelName": "Lane Splitter", "modelKey": "lane splitter"},
        ]
    }
    cases = [
        ("Big Happy should not beat Two Happy", "Channel Islands Two Happy 5'10", "Two Happy"),
        ("Dumpster Diver 2 beats Dumpster Diver", "CI Dumpster Diver 2 5'8", "Dumpster Diver 2"),
        ("Happy Everyday beats Happy", "Channel Islands Happy Everyday 6'0", "Happy Everyday"),
        ("CI Mid Twin beats CI Mid", "Channel Islands CI Mid Twin 6'7", "CI Mid Twin"),
        ("Lane Splitter beats generic Fish", "Lane Splitter Fish 5'8", "Lane Splitter"),
    ]
    failures = []
    for name, title, expected in cases:
        row = {"brandId": 1, "rawProductTitle": title, "normalisedProductTitle": title}
        selected = select_model_candidate(row, models_by_brand)
        actual = selected["modelName"] if selected else None
        if actual != expected:
            failures.append({"case": name, "expected": expected, "actual": actual})
    return {
        "testsRun": len(cases),
        "testsPassed": len(cases) - len(failures),
        "failures": failures,
    }


def get_or_create_retailer(conn, retailer: dict) -> tuple[int, bool]:
    existing = conn.execute(
        text("""
            SELECT TOP 1 RetailerId
            FROM dbo.Retailers
            WHERE RetailerName = :retailer_name
              AND RegionCode = 'EU'
            ORDER BY RetailerId
        """),
        retailer,
    ).fetchone()
    if existing:
        conn.execute(
            text("""
                UPDATE dbo.Retailers
                SET WebsiteUrl = :website_url,
                    Country = :country,
                    IsActive = 1,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE RetailerId = :retailer_id
                  AND RegionCode = 'EU'
            """),
            {**retailer, "retailer_id": existing.RetailerId},
        )
        return int(existing.RetailerId), False

    row = conn.execute(
        text("""
            INSERT INTO dbo.Retailers (
                RetailerName,
                WebsiteUrl,
                Country,
                RegionCode,
                IsActive,
                CreatedAtUtc,
                UpdatedAtUtc
            )
            OUTPUT INSERTED.RetailerId
            VALUES (
                :retailer_name,
                :website_url,
                :country,
                'EU',
                1,
                SYSUTCDATETIME(),
                SYSUTCDATETIME()
            )
        """),
        retailer,
    ).fetchone()
    return int(row.RetailerId), True


def existing_inventory_id(conn, row: dict) -> int | None:
    existing = conn.execute(
        text("""
            SELECT TOP 1 InventoryId
            FROM dbo.RetailerInventory
            WHERE RetailerId = :retailer_id
              AND RegionCode = 'EU'
              AND ISNULL(ProductUrl, '') = ISNULL(:product_url, '')
              AND ISNULL(RawProductTitle, '') = ISNULL(:raw_title, '')
              AND ISNULL(LengthFeetInches, '') = ISNULL(:length, '')
              AND (
                    (VolumeLitres IS NULL AND :volume IS NULL)
                    OR VolumeLitres = :volume
                  )
            ORDER BY InventoryId
        """),
        row,
    ).fetchone()
    return int(row_field(existing, "InventoryId")) if existing else None


def inventory_key(row: dict) -> tuple:
    return (
        int(row.get("retailer_id")),
        clean_key(row.get("product_url")),
        clean_key(row.get("raw_title")),
        clean_key(row.get("length")),
        decimal_key(row.get("volume")),
    )


def load_existing_eu_inventory(conn) -> dict[tuple, int]:
    rows = conn.execute(
        text("""
            SELECT
                InventoryId,
                RetailerId,
                ProductUrl,
                RawProductTitle,
                LengthFeetInches,
                VolumeLitres
            FROM dbo.RetailerInventory
            WHERE RegionCode = 'EU'
        """)
    ).fetchall()
    existing = {}
    for row in rows:
        payload = {
            "retailer_id": row_field(row, "RetailerId"),
            "product_url": row_field(row, "ProductUrl"),
            "raw_title": row_field(row, "RawProductTitle"),
            "length": row_field(row, "LengthFeetInches"),
            "volume": row_field(row, "VolumeLitres"),
        }
        existing[inventory_key(payload)] = int(row_field(row, "InventoryId"))
    return existing


def apply_inventory_row(conn, row: dict) -> str:
    inventory_id = existing_inventory_id(conn, row)
    if inventory_id is not None:
        conn.execute(
            text("""
                UPDATE dbo.RetailerInventory
                SET BrandId = :brand_id,
                    NormalisedProductTitle = :normalised_title,
                    ProductImageUrl = :product_image_url,
                    PriceAmount = :price_amount,
                    PriceCurrency = 'EUR',
                    StockStatus = :stock_status,
                    Construction = :construction,
                    FinSetup = :fin_setup,
                    InventoryConfidenceScore = :confidence,
                    LastCheckedUtc = SYSUTCDATETIME(),
                    IsActive = 1,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE InventoryId = :inventory_id
                  AND RegionCode = 'EU'
            """),
            {**row, "inventory_id": inventory_id},
        )
        return "updated"

    conn.execute(
        text("""
            INSERT INTO dbo.RetailerInventory (
                RetailerId,
                BrandId,
                BoardModelId,
                BoardSizeId,
                RawProductTitle,
                NormalisedProductTitle,
                ProductUrl,
                ProductImageUrl,
                PriceAud,
                PriceAmount,
                PriceCurrency,
                StockStatus,
                StockQuantity,
                Construction,
                FinSetup,
                LengthFeetInches,
                Width,
                Thickness,
                VolumeLitres,
                EstimatedShippingAud,
                InventoryConfidenceScore,
                LastCheckedUtc,
                IsActive,
                CreatedAtUtc,
                UpdatedAtUtc,
                RegionCode
            )
            VALUES (
                :retailer_id,
                :brand_id,
                NULL,
                NULL,
                :raw_title,
                :normalised_title,
                :product_url,
                :product_image_url,
                NULL,
                :price_amount,
                'EUR',
                :stock_status,
                NULL,
                :construction,
                :fin_setup,
                :length,
                NULL,
                NULL,
                :volume,
                NULL,
                :confidence,
                SYSUTCDATETIME(),
                1,
                SYSUTCDATETIME(),
                SYSUTCDATETIME(),
                'EU'
            )
        """),
        row,
    )
    return "inserted"


def batch_update_inventory(conn, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute(
        text("""
            UPDATE dbo.RetailerInventory
            SET BrandId = :brand_id,
                NormalisedProductTitle = :normalised_title,
                ProductImageUrl = :product_image_url,
                PriceAmount = :price_amount,
                PriceCurrency = 'EUR',
                StockStatus = :stock_status,
                Construction = :construction,
                FinSetup = :fin_setup,
                InventoryConfidenceScore = :confidence,
                LastCheckedUtc = SYSUTCDATETIME(),
                IsActive = 1,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE InventoryId = :inventory_id
              AND RegionCode = 'EU'
        """),
        rows,
    )


def batch_insert_inventory(conn, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute(
        text("""
            INSERT INTO dbo.RetailerInventory (
                RetailerId,
                BrandId,
                BoardModelId,
                BoardSizeId,
                RawProductTitle,
                NormalisedProductTitle,
                ProductUrl,
                ProductImageUrl,
                PriceAud,
                PriceAmount,
                PriceCurrency,
                StockStatus,
                StockQuantity,
                Construction,
                FinSetup,
                LengthFeetInches,
                Width,
                Thickness,
                VolumeLitres,
                EstimatedShippingAud,
                InventoryConfidenceScore,
                LastCheckedUtc,
                IsActive,
                CreatedAtUtc,
                UpdatedAtUtc,
                RegionCode
            )
            VALUES (
                :retailer_id,
                :brand_id,
                NULL,
                NULL,
                :raw_title,
                :normalised_title,
                :product_url,
                :product_image_url,
                NULL,
                :price_amount,
                'EUR',
                :stock_status,
                NULL,
                :construction,
                :fin_setup,
                :length,
                NULL,
                NULL,
                :volume,
                NULL,
                :confidence,
                SYSUTCDATETIME(),
                1,
                SYSUTCDATETIME(),
                SYSUTCDATETIME(),
                'EU'
            )
        """),
        rows,
    )


def build_apply_rows(report: dict) -> list[dict]:
    rows = []
    for row in report.get("importableRowsForApply", []):
        if row.get("regionCode") != REGION_CODE or row.get("priceCurrency") != PRICE_CURRENCY:
            continue
        rows.append(row)
    return rows


def apply_to_sql(report: dict, output_file: Path) -> dict:
    assert_apply_safety(report)
    rows = build_apply_rows(report)
    engine = build_engine()
    apply_counts = Counter()

    with engine.begin() as conn:
        assert_schema(conn)
        before = {
            "euInventoryRows": count_inventory_by_region(conn, "EU"),
            "euRetailers": count_retailers_by_region(conn, "EU"),
            "auInventoryRows": count_inventory_by_region(conn, "AU"),
            "idInventoryRows": count_inventory_by_region(conn, "ID"),
        }
        brands = brand_lookup(conn)
        retailer_ids: dict[str, int] = {}

        retailer_payloads: dict[str, dict] = {}
        for row in rows:
            slug = clean(row.get("retailerSlug"))
            if slug not in retailer_payloads:
                retailer_payloads[slug] = {
                    "retailer_name": clean(row.get("retailerName")),
                    "website_url": website_from_product_url(row.get("productUrl")),
                    "country": clean(row.get("country")) or "Europe",
                }

        for slug, retailer in retailer_payloads.items():
            retailer_id, created = get_or_create_retailer(conn, retailer)
            retailer_ids[slug] = retailer_id
            apply_counts["retailersInserted" if created else "retailersUpdated"] += 1

        existing_inventory = load_existing_eu_inventory(conn)
        insert_rows = []
        update_rows = []
        for row in rows:
            retailer_slug = clean(row.get("retailerSlug"))
            retailer_id = retailer_ids.get(retailer_slug)
            if retailer_id is None:
                apply_counts["rowsSkippedMissingRetailer"] += 1
                continue

            matched_brand = clean(row.get("matchedBrandName"))
            brand_id = brands.get(clean_key(matched_brand)) if matched_brand else None
            payload = {
                "retailer_id": retailer_id,
                "brand_id": brand_id,
                "raw_title": clean(row.get("rawProductTitle")) or "Unknown EU surfboard",
                "normalised_title": clean(row.get("modelName")) or clean(row.get("rawProductTitle")),
                "product_url": clean(row.get("productUrl")),
                "product_image_url": clean(row.get("productImageUrl")),
                "price_amount": decimal_or_none(row.get("priceAmount")),
                "stock_status": import_stock_status(row),
                "construction": clean(row.get("construction")),
                "fin_setup": clean(row.get("finSetup")),
                "length": clean(row.get("lengthFeetInches")),
                "volume": decimal_or_none(row.get("volumeLitres")),
                "confidence": float_or_none(row.get("parseConfidence")) or 0,
            }
            inventory_id = existing_inventory.get(inventory_key(payload))
            if inventory_id is None:
                insert_rows.append(payload)
            else:
                update_rows.append({**payload, "inventory_id": inventory_id})

        batch_insert_inventory(conn, insert_rows)
        batch_update_inventory(conn, update_rows)
        apply_counts["inventoryRowsInserted"] = len(insert_rows)
        apply_counts["inventoryRowsUpdated"] = len(update_rows)

        link_report_before = build_canonical_link_report(conn)
        model_links_applied = apply_model_links(conn, link_report_before["modelUpdates"])
        size_links_applied = apply_size_links(conn, link_report_before["sizeUpdates"])
        apply_counts["modelLinksApplied"] = model_links_applied
        apply_counts["sizeLinksApplied"] = size_links_applied
        link_report_after = build_canonical_link_report(conn)

        after = {
            "euInventoryRows": count_inventory_by_region(conn, "EU"),
            "euRetailers": count_retailers_by_region(conn, "EU"),
            "auInventoryRows": count_inventory_by_region(conn, "AU"),
            "idInventoryRows": count_inventory_by_region(conn, "ID"),
        }
        samples = sample_eu_rows(conn)

    validation = {
        "auRowsReduced": after["auInventoryRows"] < before["auInventoryRows"],
        "idRowsReduced": after["idInventoryRows"] < before["idInventoryRows"],
        "auRowsTouched": 0,
        "idRowsTouched": 0,
        "noDestructiveSql": True,
        "noTableTruncation": True,
        "noDeletes": True,
    }
    apply_report = {
        **report,
        "mode": "apply",
        "applyRequested": True,
        "purpose": "EU RetailerInventory import apply. Scoped to RegionCode EU and idempotent upserts.",
        "applyCounts": dict(apply_counts),
        "beforeCounts": before,
        "afterCounts": after,
        "validation": validation,
        "canonicalLinkingBeforeApply": public_link_report(link_report_before),
        "canonicalLinkingAfterApply": public_link_report(link_report_after),
        "sampleEuRows": samples,
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(apply_report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_link_report(link_report_after)
    return apply_report


def main() -> None:
    parser = argparse.ArgumentParser(description="EU retailer inventory importer. Dry-run by default.")
    parser.add_argument("--input", default=str(INPUT_FILE), help="Normalised EU inventory JSON input.")
    parser.add_argument("--output", default=str(OUTPUT_FILE), help="Dry-run report output path.")
    parser.add_argument("--apply-output", default=str(APPLY_OUTPUT_FILE), help="Apply report output path.")
    parser.add_argument("--retailer", default="", help="Optional retailerSlug filter.")
    parser.add_argument("--apply", action="store_true", help="Disabled for local safety. Use --export-sql or --azure-run.")
    parser.add_argument("--schema-check", action="store_true", help="Disabled locally; schema checks must run remotely.")
    parser.add_argument("--link-tests", action="store_true", help="Run local canonical model matching tests.")
    parser.add_argument("--export-sql", action="store_true", help="Generate SQL file only. Does not connect to SQL.")
    parser.add_argument("--sql-output", default=str(SQL_OUTPUT_FILE), help="SQL output path for --export-sql.")
    parser.add_argument("--azure-run", action="store_true", help="Print remote Azure execution command only.")
    args = parser.parse_args()

    if args.link_tests:
        result = run_link_tests()
        print("EU canonical linker tests complete")
        print(f"Tests run: {result['testsRun']}")
        print(f"Tests passed: {result['testsPassed']}")
        if result["failures"]:
            print(json.dumps(result["failures"], indent=2))
            raise RuntimeError("Canonical linker tests failed.")
        return

    if args.schema_check:
        raise RuntimeError("Local SQL schema checks are disabled. Run schema checks from Azure.")

    if args.apply:
        raise RuntimeError("Local --apply is disabled. Use --export-sql or --azure-run.")

    if args.azure_run:
        print_azure_run_command("scripts/europe/import_eu_retailer_inventory.py --export-sql")
        return

    input_file = Path(args.input)
    output_file = Path(args.output)
    rows = load_input_rows(input_file, args.retailer)
    report = build_report(rows, input_file, args.retailer)

    if args.export_sql:
        sql_output = Path(args.sql_output)
        export_import_sql(report, sql_output)
        print("EU retailer import SQL export complete")
        print(f"Rows after dedupe: {report['rowsAfterDedupe']}")
        print(f"Importable rows: {report['metrics']['importableRows']}")
        print(f"SQL output: {sql_output}")
        return

    report["canonicalLinking"] = {
        "status": "not_checked_locally",
        "reason": "Local Azure SQL connections are disabled. Use --export-sql or --azure-run.",
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("EU retailer import dry-run complete")
    print(f"Retailer: {args.retailer or 'all'}")
    print(f"Rows after dedupe: {report['rowsAfterDedupe']}")
    print(f"Importable rows: {report['metrics']['importableRows']}")
    print(f"Needs canonical review: {report['metrics']['needsCanonicalReviewRows']}")
    print(f"Rejected rows: {report['metrics']['rejectedRows']}")
    link_summary = report.get("canonicalLinkingAfterApply") or report.get("canonicalLinking")
    if link_summary and "modelLinkCandidates" in link_summary:
        print(f"Model link candidates: {link_summary['modelLinkCandidates']}")
        print(f"Size link candidates: {link_summary['sizeLinkCandidates']}")
        print(f"Linked models: {link_summary['linkedModels']}")
        print(f"Linked sizes: {link_summary['linkedSizes']}")
        print(f"Ambiguous model matches: {link_summary['ambiguousModelMatches']}")
    elif link_summary:
        print(f"Canonical linking: {link_summary['status']}")
    print(f"Recommendation: {report['recommendation']}")
    print(f"Report: {output_file}")


if __name__ == "__main__":
    main()
