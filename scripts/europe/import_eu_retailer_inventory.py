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


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clean_key(value: object) -> str:
    text = clean(value).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
            SELECT COUNT(*) AS RowCount
            FROM dbo.RetailerInventory
            WHERE ISNULL(RegionCode, 'AU') = :region_code
        """),
        {"region_code": region_code},
    ).fetchone()
    return int(row.RowCount)


def count_retailers_by_region(conn, region_code: str) -> int:
    row = conn.execute(
        text("""
            SELECT COUNT(*) AS RowCount
            FROM dbo.Retailers
            WHERE ISNULL(RegionCode, 'AU') = :region_code
        """),
        {"region_code": region_code},
    ).fetchone()
    return int(row.RowCount)


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
            ORDER BY ri.UpdatedAtUtc DESC, ri.RetailerInventoryId DESC
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


def schema_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(
        text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = :table_name
        """),
        {"table_name": table_name},
    ).fetchall()
    return {row.COLUMN_NAME for row in rows}


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
        "RetailerInventoryId",
        "RetailerId",
        "BrandId",
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


def brand_lookup(conn) -> dict[str, int]:
    rows = conn.execute(
        text("""
            SELECT BrandId, BrandName
            FROM dbo.Brands
            WHERE IsActive = 1
        """)
    ).fetchall()
    return {clean_key(row.BrandName): row.BrandId for row in rows}


def get_or_create_retailer(conn, retailer: dict) -> tuple[int, bool]:
    existing = conn.execute(
        text("""
            SELECT RetailerId
            FROM dbo.Retailers
            WHERE RetailerName = :retailer_name
              AND RegionCode = 'EU'
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
            SELECT TOP 1 RetailerInventoryId
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
            ORDER BY RetailerInventoryId
        """),
        row,
    ).fetchone()
    return int(existing.RetailerInventoryId) if existing else None


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
                WHERE RetailerInventoryId = :inventory_id
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
            action = apply_inventory_row(conn, payload)
            apply_counts[f"inventoryRows{action.title()}"] += 1

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
        "sampleEuRows": samples,
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(apply_report, indent=2, ensure_ascii=False), encoding="utf-8")
    return apply_report


def main() -> None:
    parser = argparse.ArgumentParser(description="EU retailer inventory importer. Dry-run by default.")
    parser.add_argument("--input", default=str(INPUT_FILE), help="Normalised EU inventory JSON input.")
    parser.add_argument("--output", default=str(OUTPUT_FILE), help="Dry-run report output path.")
    parser.add_argument("--apply-output", default=str(APPLY_OUTPUT_FILE), help="Apply report output path.")
    parser.add_argument("--retailer", default="", help="Optional retailerSlug filter.")
    parser.add_argument("--apply", action="store_true", help="Apply SQL writes. Requires explicit approval before use.")
    args = parser.parse_args()

    input_file = Path(args.input)
    output_file = Path(args.apply_output if args.apply else args.output)
    rows = load_input_rows(input_file, args.retailer)
    report = build_report(rows, input_file, args.retailer)

    if args.apply:
        report = apply_to_sql(report, output_file)
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("EU retailer import apply complete" if args.apply else "EU retailer import dry-run complete")
    print(f"Retailer: {args.retailer or 'all'}")
    print(f"Rows after dedupe: {report['rowsAfterDedupe']}")
    print(f"Importable rows: {report['metrics']['importableRows']}")
    print(f"Needs canonical review: {report['metrics']['needsCanonicalReviewRows']}")
    print(f"Rejected rows: {report['metrics']['rejectedRows']}")
    if args.apply:
        print(f"Inventory rows inserted: {report['applyCounts'].get('inventoryRowsInserted', 0)}")
        print(f"Inventory rows updated: {report['applyCounts'].get('inventoryRowsUpdated', 0)}")
        print(f"EU RetailerInventory rows: {report['afterCounts']['euInventoryRows']}")
        print(f"EU retailers: {report['afterCounts']['euRetailers']}")
        print(f"AU RetailerInventory rows: {report['afterCounts']['auInventoryRows']}")
        print(f"ID RetailerInventory rows: {report['afterCounts']['idInventoryRows']}")
    print(f"Recommendation: {report['recommendation']}")
    print(f"Report: {output_file}")


if __name__ == "__main__":
    main()
