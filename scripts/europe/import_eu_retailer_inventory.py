from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError, OperationalError


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


INPUT_FILE = Path("scrapers/retailers/europe/output/eu_normalised_inventory.json")
BRANDS_FILE = Path("scrapers/brands/brands_seed.json")
BRAND_OUTPUT_ROOT = Path("scrapers/brands")
OUTPUT_FILE = Path("scripts/europe/output/eu_retailer_import_dry_run_report.json")
APPLY_OUTPUT_FILE = Path("scripts/europe/output/eu_retailer_import_apply_report.json")
LINK_REPORT_FILE = Path("scripts/europe/output/eu_retailer_canonical_link_report.json")
LINK_APPLY_REPORT_FILE = Path("scripts/europe/output/eu_canonical_link_apply_report.json")
SQL_OUTPUT_FILE = Path("scripts/europe/output/eu_import.sql")

REGION_CODE = "EU"
PRICE_CURRENCY = "EUR"

BRAND_ALIASES = {
    "aloha": "Aloha",
    "al merrick": "Channel Islands",
    "channel islands": "Channel Islands",
    "channel island": "Channel Islands",
    "channel island surfboards": "Channel Islands",
    "channel islands surfboards": "Channel Islands",
    "ci": "Channel Islands",
    "ci surfboards": "Channel Islands",
    "js": "JS Industries",
    "js industries": "JS Industries",
    "js industries surfboards": "JS Industries",
    "lost": "Lost",
    "hayden shapes": "Haydenshapes",
    "haydenshapes surfboards": "Haydenshapes",
    "lost surfboards": "Lost",
    "mayhem": "Lost",
    "firewire": "Firewire",
    "firewire surfboards": "Firewire",
    "pyzel": "Pyzel",
    "pyzel surfboards": "Pyzel",
    "dhd": "DHD",
    "dhd surfboards": "DHD",
    "pukas": "Pukas",
    "pukas surfboards": "Pukas",
    "christenson": "Christenson",
    "christenson surfboards": "Christenson",
    "chilli": "Chilli",
    "chilli surfboards": "Chilli",
    "haydenshapes": "Haydenshapes",
    "haydenshapes surfboards": "Haydenshapes",
    "nsp": "NSP",
    "nsp surfboards": "NSP",
    "rusty": "Rusty",
    "rusty surfboards": "Rusty",
    "slater designs": "Slater Designs",
    "slater designs surfboards": "Slater Designs",
    "torq": "Torq",
    "torq surfboards": "Torq",
    "sharp eye": "Sharp Eye",
    "sharpeye": "Sharp Eye",
    "sharpeye surfboards": "Sharp Eye",
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

DETERMINISTIC_MODEL_ALIASES = {
    "fishbeard": "fish beard",
    "high line": "highline",
    "hk twin": "hk twin pin",
    "mav s gun": "mavs gun",
    "mikey s shorty": "mikey february shorty",
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


def model_key(value: object) -> str:
    text_value = clean(value).lower().replace("&", " and ")
    text_value = re.sub(r"(?<=\d)\.0\b", "", text_value)
    text_value = re.sub(r"[^a-z0-9]+", " ", text_value)
    text_value = re.sub(r"\bii\b", "2", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def measurement_key(value: object) -> Fraction | None:
    """Normalise decimal and surf-fraction measurements for exact comparison."""
    value = clean(value).replace('"', "").strip()
    if not value:
        return None
    match = re.fullmatch(r"(\d+)(?:\s+(\d+)\s*/\s*(\d+))?", value)
    if match:
        result = Fraction(int(match.group(1)), 1)
        if match.group(2):
            result += Fraction(int(match.group(2)), int(match.group(3)))
        return result
    try:
        return Fraction(Decimal(value)).limit_denominator(16)
    except (InvalidOperation, ValueError, ZeroDivisionError):
        return None


def construction_key(value: object) -> str:
    key = clean_key(value)
    aliases = {
        "carbon tune": "carbotune",
        "hyfi 3": "hyfi",
        "hyfi 3 0": "hyfi",
        "i bolic": "ibolic",
        "i bolic 2 0": "ibolic",
        "pu stringer": "pu",
        "polyester": "pu",
    }
    return aliases.get(key, key)


def tolerant_model_key(value: object) -> str:
    """Remove only obvious merchandising suffixes after brand confidence exists."""
    key = model_key(value)
    key = re.sub(r"\s+by\s+[a-z][a-z ]+$", "", key)
    key = re.sub(
        r"\s+(?:white|black|blue|navy|red|orange|yellow|green|grey|gray|pink|sand|"
        r"clear|color|colour|new|used|in stock|out of stock|pre order)$",
        "",
        key,
    )
    key = re.sub(r"\s+[a-z]{1,4}\d{4,}$", "", key)
    key = key.strip()
    return DETERMINISTIC_MODEL_ALIASES.get(key, key)


def clean_model_hint(value: object) -> str:
    """Remove deterministic retailer metadata after isolating the model text."""
    model = clean(value)
    model = re.sub(
        r"\s+-\s+(?=(?:[4-9]|1[0-2])\s*['’]\s*\d{1,2}\b).*$",
        "",
        model,
        flags=re.IGNORECASE,
    )
    model = re.sub(r"\s+by\s+[A-Za-z][A-Za-z .'-]*$", "", model, flags=re.IGNORECASE)
    model = re.sub(
        r"\s+(?:white|black|blue|navy|red|orange|yellow|green|grey|gray|pink|"
        r"sand|coral|mustard|burgundy|cream|taupe|olive|mint|clear|color|colour)$",
        "",
        model,
        flags=re.IGNORECASE,
    )
    return clean(model)


def catalogue_model_key(model_name: object, brand_name: object) -> str:
    key = model_key(model_name)
    brand = model_key(brand_name)
    if brand and key.startswith(f"{brand} "):
        return key[len(brand) + 1 :]
    return key


def extract_canonical_brand_name(title: object, existing_brand: object = "") -> str:
    existing_key = clean_key(existing_brand)
    for alias, canonical in BRAND_ALIASES.items():
        if existing_key == clean_key(alias) or existing_key == clean_key(canonical):
            return canonical

    title_key = re.sub(r"^surfboards?\s+", "", clean_key(title))
    for alias, canonical in sorted(
        BRAND_ALIASES.items(), key=lambda item: len(clean_key(item[0])), reverse=True
    ):
        alias_key = clean_key(alias)
        if title_key == alias_key or title_key.startswith(f"{alias_key} "):
            return canonical
    return ""


def extract_model_hint(title: object, brand_name: object = "") -> str:
    value = clean(title)
    if not value:
        return ""

    parts = [clean(part) for part in re.split(r"\s+-\s+", value) if clean(part)]
    if (
        len(parts) >= 2
        and re.fullmatch(r".+?\s+surfboards?", parts[0], re.IGNORECASE)
        and not re.search(r"\d\s*['’]", parts[0])
    ):
        return clean_model_hint(parts[1])

    value = re.sub(r"^PRE\s*ORDER\s*\|\s*", "", value, flags=re.IGNORECASE)
    aliases = sorted(
        {*BRAND_ALIASES.keys(), clean(brand_name)}, key=len, reverse=True
    )
    for alias in aliases:
        if alias:
            value = re.sub(
                rf"^{re.escape(alias)}(?:\s+surfboards?)?\s*[-|:]?\s*",
                "",
                value,
                flags=re.IGNORECASE,
            )
            if value != clean(title):
                break

    value = re.sub(r"^surfboards?\s*[-|:]?\s*", "", value, flags=re.IGNORECASE)
    for alias in aliases:
        if alias:
            updated = re.sub(
                rf"^{re.escape(alias)}(?:\s+surfboards?)?\s*[-|:]?\s*",
                "",
                value,
                flags=re.IGNORECASE,
            )
            if updated != value:
                value = updated
                break
    value = re.sub(
        r"^(?:[4-9]|1[0-2])\s*['’]\s*\d{1,2}\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.split(
        r"\b(?:PU|EPS|SPINE\s*-?\s*TEK|LIGHT\s*SPEED|LIGHTSPEED|"
        r"HELIUM|IBOLIC|VOLCANIC|LFT|FST|PE|TIMBERTEK|THUNDERBOLT)\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    value = re.split(
        r"\b(?:round\s+pin|round|squash|swallow|fish|diamond|square)\s+tail\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    value = re.sub(r"\s+[-|]\s+(?:white|color|colour).*$", "", value, flags=re.IGNORECASE)
    return clean_model_hint(value)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def build_connection_string() -> str:
    load_dotenv()
    server = require_env("SQL_SERVER").replace("tcp:", "").strip()
    database = require_env("SQL_DATABASE")
    username = require_env("SQL_USERNAME")
    password = require_env("SQL_PASSWORD")
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server").strip()

    if not server.endswith(".database.windows.net"):
        raise RuntimeError(
            "SQL_SERVER must be the Azure SQL server host only, for example "
            "quivrr-sql-prod.database.windows.net"
        )

    odbc_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER=tcp:{server},1433;"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
    )
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_string)


def build_engine():
    engine = create_engine(
        build_connection_string(),
        pool_pre_ping=True,
        pool_recycle=120,
        pool_size=5,
        max_overflow=10,
        connect_args={"timeout": 60},
    )

    @event.listens_for(engine, "before_cursor_execute")
    def enable_fast_executemany(conn, cursor, statement, parameters, context, executemany):
        if executemany:
            cursor.fast_executemany = True

    return engine


def connect_with_retry(engine, attempts: int = 5):
    last_error = None
    for attempt in range(1, attempts + 1):
        connection = None
        try:
            connection = engine.connect()
            connection.execute(text("SELECT 1"))
            connection.rollback()
            return connection
        except (OperationalError, DBAPIError) as error:
            if connection is not None:
                connection.close()
            last_error = error
            if attempt == attempts:
                raise
            print(
                f"SQL connection attempt {attempt}/{attempts} failed; retrying",
                flush=True,
            )
            time.sleep(min(10, 1.5 * attempt))
    raise last_error


@contextmanager
def begin_with_retry(engine, attempts: int = 5):
    connection = connect_with_retry(engine, attempts=attempts)
    try:
        with connection.begin():
            yield connection
    finally:
        connection.close()


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
    invalid_regions = [
        (index, row.get("retailerSlug"), row.get("regionCode"))
        for index, row in enumerate(rows)
        if row.get("regionCode") != REGION_CODE
    ]
    if invalid_regions:
        index, slug, region = invalid_regions[0]
        raise RuntimeError(
            "EU import safety failed at input row "
            f"{index} ({slug or '<missing>'}): RegionCode must be 'EU', got {region!r}."
        )
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
    retailer_diagnostics: dict[str, Counter] = defaultdict(Counter)

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
        slug = dry_row["retailerSlug"] or "<missing>"
        retailer_diagnostics[slug]["normalisedSurfboards"] += 1

        for reject in rejects:
            true_reject_counts[reject] += 1
            retailer_diagnostics[slug][f"reject:{reject}"] += 1
        for item in reason.split(",") if reason else []:
            review_reason_counts[item] += 1

        if not match["canonicalBrandMatched"]:
            unknown_brands[clean(row.get("brandName")) or "missing"] += 1
        if not match["canonicalModelMatched"]:
            unknown_models[
                f"{clean(row.get('brandName')) or 'missing_brand'} / {clean(row.get('modelName')) or 'missing_model'}"
            ] += 1

        if importable_raw:
            retailer_diagnostics[slug]["importRows"] += 1
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
        "perRetailerDiagnostics": {
            slug: {
                "normalisedSurfboards": counts["normalisedSurfboards"],
                "importRows": counts["importRows"],
                "linkedBoardModelIdRows": 0,
                "linkedBoardSizeIdRows": 0,
                "rejectReasonCounts": {
                    key.removeprefix("reject:"): value
                    for key, value in sorted(counts.items())
                    if key.startswith("reject:")
                },
            }
            for slug, counts in sorted(retailer_diagnostics.items())
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
    if report.get("metrics", {}).get("importableRows", 0) <= 0:
        raise RuntimeError("Safety check failed: no importable EU rows were produced.")


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


def priority_retailer_counts(conn) -> list[dict]:
    rows = conn.execute(
        text("""
            SELECT
                r.RegionCode,
                r.RetailerName,
                COUNT(ri.InventoryId) AS InventoryRows,
                SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModels,
                SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizes
            FROM dbo.Retailers r
            LEFT JOIN dbo.RetailerInventory ri
              ON ri.RetailerId = r.RetailerId
             AND ri.RegionCode = r.RegionCode
            WHERE r.RetailerName IN ('58 Surf', 'Pukas Surf Shop')
            GROUP BY r.RegionCode, r.RetailerName
            ORDER BY r.RegionCode, r.RetailerName
        """),
    ).fetchall()
    return [
        {
            "regionCode": clean(row_field(row, "RegionCode")),
            "retailerName": clean(row_field(row, "RetailerName")),
            "inventoryRows": int(row_field(row, "InventoryRows") or 0),
            "linkedBoardModelIdRows": int(row_field(row, "LinkedModels") or 0),
            "linkedBoardSizeIdRows": int(row_field(row, "LinkedSizes") or 0),
        }
        for row in rows
    ]


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
    with connect_with_retry(engine) as conn:
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
                bm.BoardModelId,
                bm.BrandId,
                bm.ModelName,
                b.BrandName
            FROM dbo.BoardModels bm
            INNER JOIN dbo.Brands b ON b.BrandId = bm.BrandId
            WHERE bm.IsActive = 1
        """)
    ).fetchall()
    models: dict[int, list[dict]] = {}
    for row in rows:
        model = {
            "boardModelId": int(row_field(row, "BoardModelId")),
            "brandId": int(row_field(row, "BrandId")),
            "modelName": clean(row_field(row, "ModelName")),
            "modelKey": catalogue_model_key(
                row_field(row, "ModelName"), row_field(row, "BrandName")
            ),
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
                Width,
                Thickness,
                VolumeLitres,
                Construction
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
            "width": clean(row_field(row, "Width")),
            "thickness": clean(row_field(row, "Thickness")),
            "volumeLitres": decimal_or_none(row_field(row, "VolumeLitres")),
            "construction": clean(row_field(row, "Construction")),
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
                ri.Width,
                ri.Thickness,
                ri.VolumeLitres,
                ri.Construction,
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
            "width": clean(row_field(row, "Width")),
            "thickness": clean(row_field(row, "Thickness")),
            "volumeLitres": decimal_or_none(row_field(row, "VolumeLitres")),
            "construction": clean(row_field(row, "Construction")),
            "priceCurrency": clean(row_field(row, "PriceCurrency")),
            "regionCode": clean(row_field(row, "RegionCode")),
        })
    return inventory


def score_model_candidate(row: dict, model: dict) -> int | None:
    candidate_key = model["modelKey"]
    raw_key = model_key(row.get("rawProductTitle"))
    normalised_key = model_key(row.get("normalisedProductTitle"))
    hint_key = tolerant_model_key(
        row.get("parsedModel")
        or extract_model_hint(row.get("rawProductTitle"), row.get("brandName"))
    )
    score = None

    if hint_key and hint_key == candidate_key:
        score = 14000
    elif hint_key and hint_key.startswith(f"{candidate_key} "):
        score = 11000
    elif normalised_key and normalised_key == candidate_key:
        score = 10000
    elif f" {candidate_key} " in f" {normalised_key} ":
        score = 7000
    elif f" {candidate_key} " in f" {raw_key} ":
        if hint_key and not hint_key.startswith(candidate_key):
            return None
        score = 5000

    if score is None:
        return None

    score += len(candidate_key) * 10
    if candidate_key in {model_key(name) for name in GENERIC_MODEL_NAMES}:
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
            "isGeneric": model["modelKey"] in {model_key(name) for name in GENERIC_MODEL_NAMES},
        })
    candidates.sort(key=lambda item: (item["score"], len(model_key(item["modelName"]))), reverse=True)
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
    same_length = [
        size
        for size in sizes_by_model.get(board_model_id, [])
        if clean(size.get("lengthFeetInches")) == length
    ]
    if not same_length:
        return None

    if row_volume is None:
        candidates = [dict(size) for size in same_length]
        tolerance = "length_only_no_retailer_volume"
    else:
        measured = []
        for size in same_length:
            size_volume = decimal_or_none(size.get("volumeLitres"))
            if size_volume is None:
                continue
            item = dict(size)
            item["volumeDelta"] = abs(row_volume - size_volume)
            measured.append(item)

        tiers = [
            ("exact", lambda delta: delta == 0),
            ("plus_minus_0_05", lambda delta: delta <= Decimal("0.05")),
            ("plus_minus_0_10", lambda delta: delta <= Decimal("0.10")),
            ("plus_minus_0_20", lambda delta: delta <= Decimal("0.20")),
        ]
        candidates = []
        tolerance = None
        for tier_name, predicate in tiers:
            candidates = [item for item in measured if predicate(item["volumeDelta"])]
            if candidates:
                tolerance = tier_name
                break
        if not candidates:
            return None

    initial_count = len(candidates)
    filters = (
        ("width", measurement_key),
        ("thickness", measurement_key),
        ("construction", construction_key),
    )
    for field, normaliser in filters:
        source_key = normaliser(row.get(field))
        if source_key in (None, ""):
            continue
        exact = [item for item in candidates if normaliser(item.get(field)) == source_key]
        if exact:
            candidates = exact

    if len(candidates) != 1:
        return None

    selected_size = candidates[0]
    size_volume = decimal_or_none(selected_size.get("volumeLitres"))
    volume_delta = selected_size.get("volumeDelta")
    return {
        "boardSizeId": selected_size["boardSizeId"],
        "lengthFeetInches": selected_size["lengthFeetInches"],
        "volumeLitres": float(size_volume) if size_volume is not None else None,
        "volumeDelta": float(volume_delta) if volume_delta is not None else None,
        "volumeTolerance": tolerance,
        "candidateCount": initial_count,
    }


def build_canonical_link_report(conn) -> dict:
    inventory_rows = load_eu_inventory_rows(conn)
    brands = brand_lookup(conn)
    models_by_brand = load_board_models(conn)
    sizes_by_model = load_board_sizes(conn)
    brand_updates = []
    model_updates = []
    size_updates = []
    ambiguous = []
    unmatched_by_retailer = Counter()
    unmatched_by_brand = Counter()
    unmatched_models = Counter()
    failed_patterns = Counter()
    unlinked_rows = []
    retailer_metrics: dict[str, Counter] = defaultdict(Counter)

    linked_models = 0
    linked_sizes = 0

    for row in inventory_rows:
        retailer_name = row["retailerName"] or "missing"
        metrics = retailer_metrics[retailer_name]
        metrics["totalRows"] += 1
        parsed_brand = extract_canonical_brand_name(
            row.get("rawProductTitle"), row.get("brandName")
        )
        parsed_model = extract_model_hint(row.get("rawProductTitle"), parsed_brand)
        effective_brand_id = row.get("brandId")
        if effective_brand_id is None and parsed_brand:
            effective_brand_id = brands.get(clean_key(parsed_brand))
            if effective_brand_id is not None:
                brand_updates.append({
                    "inventory_id": row["inventoryId"],
                    "brand_id": effective_brand_id,
                })

        match_row = {
            **row,
            "brandId": effective_brand_id,
            "brandName": parsed_brand or row.get("brandName"),
            "parsedModel": parsed_model,
        }
        selected_model = None
        effective_model_id = row.get("boardModelId")

        if effective_model_id is not None:
            linked_models += 1
            metrics["linkedBoardModelIdRows"] += 1
        else:
            selected_model = select_model_candidate(match_row, models_by_brand)
            if selected_model:
                effective_model_id = selected_model["boardModelId"]
                model_updates.append({
                    "inventory_id": row["inventoryId"],
                    "board_model_id": effective_model_id,
                    "normalised_title": selected_model["modelName"],
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
                unmatched_by_retailer[retailer_name] += 1
                unmatched_by_brand[parsed_brand or row["brandName"] or "missing"] += 1
                unmatched_models[parsed_model or "missing"] += 1

        if row.get("boardSizeId") is not None:
            linked_sizes += 1
            metrics["linkedBoardSizeIdRows"] += 1
            continue

        selected_size = (
            select_size_candidate(match_row, effective_model_id, sizes_by_model)
            if effective_model_id is not None
            else None
        )
        if selected_size:
            size_updates.append({
                "inventory_id": row["inventoryId"],
                "board_size_id": selected_size["boardSizeId"],
            })

        if row.get("boardModelId") is None or row.get("boardSizeId") is None:
            reasons = []
            if effective_brand_id is None:
                reasons.append("unknown_brand")
            if row.get("boardModelId") is None:
                if selected_model:
                    reasons.append("model_link_candidate")
                elif not parsed_model:
                    reasons.append("model_parse_failed")
                else:
                    reasons.append("model_not_in_catalogue")
            if row.get("boardSizeId") is None:
                if effective_model_id is None:
                    reasons.append("size_blocked_by_model")
                elif selected_size:
                    reasons.append("size_link_candidate")
                elif not row.get("lengthFeetInches"):
                    reasons.append("missing_length")
                elif row.get("volumeLitres") is None:
                    reasons.append("ambiguous_length_without_volume")
                else:
                    reasons.append("no_size_within_volume_tolerance")

            title = row.get("rawProductTitle") or ""
            pattern = (
                "structured_brand_model_dimensions"
                if len(re.split(r"\s+-\s+", title)) >= 3
                else "brand_surfboard_length_model"
                if re.search(r"surfboards?\s+\d+\s*['’]", title, re.IGNORECASE)
                else "other_title_pattern"
            )
            failed_patterns[pattern] += 1
            unlinked_rows.append({
                "retailerName": retailer_name,
                "rawProductTitle": title,
                "parsedBrand": parsed_brand or None,
                "parsedModel": parsed_model or None,
                "lengthFeetInches": row.get("lengthFeetInches") or None,
                "width": row.get("width") or None,
                "thickness": row.get("thickness") or None,
                "volumeLitres": float(row["volumeLitres"]) if row.get("volumeLitres") is not None else None,
                "reasons": reasons,
            })

    retailer_audit = []
    for retailer_name, metrics in sorted(retailer_metrics.items()):
        total = metrics["totalRows"]
        model_count = metrics["linkedBoardModelIdRows"]
        size_count = metrics["linkedBoardSizeIdRows"]
        retailer_audit.append({
            "retailerName": retailer_name,
            "totalRows": total,
            "linkedBoardModelIdRows": model_count,
            "linkedBoardSizeIdRows": size_count,
            "unlinkedModelRows": total - model_count,
            "unlinkedSizeRows": total - size_count,
        })

    return {
        "regionCode": REGION_CODE,
        "totalEuRows": len(inventory_rows),
        "linkedModels": linked_models,
        "linkedSizes": linked_sizes,
        "retailerAudit": retailer_audit,
        "brandLinkCandidates": len(brand_updates),
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
        "topUnlinkedModels": [
            {"parsedModel": key, "count": value}
            for key, value in unmatched_models.most_common(50)
        ],
        "commonFailedTitlePatterns": [
            {"pattern": key, "count": value}
            for key, value in failed_patterns.most_common()
        ],
        "unlinkedRowSample": unlinked_rows[:250],
        "brandUpdates": brand_updates,
        "modelUpdates": model_updates,
        "sizeUpdates": size_updates,
    }


def write_link_report(report: dict, output_file: Path = LINK_REPORT_FILE) -> None:
    public_report = {
        key: value
        for key, value in report.items()
        if key not in {"brandUpdates", "modelUpdates", "sizeUpdates"}
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(public_report, indent=2, ensure_ascii=False), encoding="utf-8")


def public_link_report(report: dict) -> dict:
    return {
        key: value
        for key, value in report.items()
        if key not in {"brandUpdates", "modelUpdates", "sizeUpdates"}
    }


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
                NormalisedProductTitle = :normalised_title,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE InventoryId = :inventory_id
              AND RegionCode = 'EU'
              AND BoardModelId IS NULL
        """),
        model_updates,
    )
    return len(model_updates)


def apply_brand_links(conn, brand_updates: list[dict]) -> int:
    if not brand_updates:
        return 0
    conn.execute(
        text("""
            UPDATE dbo.RetailerInventory
            SET BrandId = :brand_id,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE InventoryId = :inventory_id
              AND RegionCode = 'EU'
              AND BrandId IS NULL
        """),
        brand_updates,
    )
    return len(brand_updates)


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
    tests_run = 0
    for name, title, expected in cases:
        tests_run += 1
        row = {"brandId": 1, "rawProductTitle": title, "normalisedProductTitle": title}
        selected = select_model_candidate(row, models_by_brand)
        actual = selected["modelName"] if selected else None
        if actual != expected:
            failures.append({"case": name, "expected": expected, "actual": actual})

    brand_cases = [
        ("CHANNEL ISLANDS SURFBOARDS - CI MID TWIN", "Channel Islands"),
        ("CI SURFBOARDS - CI MID", "Channel Islands"),
        ("JS INDUSTRIES - 3DV", "JS Industries"),
        ("LOST SURFBOARDS - RAD RIPPER", "Lost"),
        ("MAYHEM - RNF 96", "Lost"),
        ("FIREWIRE SURFBOARDS - DOMINATOR 2", "Firewire"),
        ("PYZEL SURFBOARDS - GHOST", "Pyzel"),
        ("DHD SURFBOARDS - 3DV", "DHD"),
        ("PUKAS SURFBOARDS - TWIN PIN", "Pukas"),
        ("CHRISTENSON SURFBOARDS - FISH", "Christenson"),
        ("SHARPEYE SURFBOARDS - INFERNO 72", "Sharp Eye"),
        ("Surfboard Channel Island Happy Everyday - 6'0", "Channel Islands"),
    ]
    for title, expected in brand_cases:
        tests_run += 1
        actual = extract_canonical_brand_name(title)
        if actual != expected:
            failures.append({"case": f"brand alias {title}", "expected": expected, "actual": actual})

    model_cases = [
        (
            "CHANNEL ISLANDS SURFBOARDS - CI MID TWIN - 6'7 X 20 7/8 X 2 11/16 - 40.70L - CI41738",
            "Channel Islands",
            "CI MID TWIN",
        ),
        ("PYZEL SURFBOARDS - GHOST - 6'0 X 19 X 2 1/2 - 29.10L", "Pyzel", "GHOST"),
        ("FIREWIRE SURFBOARDS - DOMINATOR 2 - 5'10 X 19 3/4 X 2 7/16 - 31.00L", "Firewire", "DOMINATOR 2"),
        ("LOST SURFBOARDS - RAD RIPPER - 5'11 X 19 1/4 X 2 7/16 - 29.50L", "Lost", "RAD RIPPER"),
        ("Surfboard Lost Round Nose Fish Redux - 5'10", "Lost", "Round Nose Fish Redux"),
        ("Surfboard Lost Mini Driver - 5'10", "Lost", "Mini Driver"),
        ("Lost Surfboards - F1 by Matt Biolos - FCS II - GREEN - PRO - 5'11\" x 18.88\"", "Lost", "F1"),
        ("Pukas Surfboards - Balloon by David Santos - 5'7\" x 20.5 x 2.73", "Pukas", "Balloon"),
        ("Aloha Surfboard 5'6 KEEL TWIN 2F CORAL PU Fish Tail - Color", "Aloha", "KEEL TWIN 2F"),
        ("JS Surfboard 5'10 RED BARON PE Swallow Tail - White", "JS Industries", "RED BARON"),
    ]
    for title, brand, expected in model_cases:
        tests_run += 1
        actual = extract_model_hint(title, brand)
        if model_key(actual) != model_key(expected):
            failures.append({"case": f"model parse {title}", "expected": expected, "actual": actual})

    alias_cases = [
        ("FISHBEARD", "Fish Beard"),
        ("HIGH LINE", "Highline"),
        ("MAV´S GUN", "Mavs Gun"),
        ("MIKEY'S SHORTY", "Mikey February Shorty"),
        ("HK TWIN", "HK Twin Pin"),
    ]
    for retailer_model, canonical_model in alias_cases:
        tests_run += 1
        actual = tolerant_model_key(retailer_model)
        expected = tolerant_model_key(canonical_model)
        if actual != expected:
            failures.append({
                "case": f"deterministic model alias {retailer_model}",
                "expected": expected,
                "actual": actual,
            })

    from scrapers.retailers.europe.normalise_eu_retailer_inventory import (
        parse_length,
        parse_volume,
    )

    dimension_cases = [
        ("6'7 X 20 7/8 X 2 11/16 - 40.70L", "6'7", 40.70),
        ("9'6 X 21 3/8 X 3 5/8 - 77,60L", "9'6", 77.60),
    ]
    for value, expected_length, expected_volume in dimension_cases:
        tests_run += 1
        actual_length = parse_length(value)
        actual_volume = parse_volume(value)
        if actual_length != expected_length or actual_volume != expected_volume:
            failures.append({
                "case": f"dimensions {value}",
                "expected": [expected_length, expected_volume],
                "actual": [actual_length, actual_volume],
            })

    sizes = {
        10: [
            {"boardSizeId": 100, "boardModelId": 10, "lengthFeetInches": "6'0", "volumeLitres": Decimal("29.10")},
            {"boardSizeId": 101, "boardModelId": 10, "lengthFeetInches": "6'1", "volumeLitres": Decimal("30.00")},
        ]
    }
    size_cases = [
        ("exact", {"lengthFeetInches": "6'0", "volumeLitres": "29.10"}, 100, "exact"),
        ("tolerance 0.05", {"lengthFeetInches": "6'0", "volumeLitres": "29.15"}, 100, "plus_minus_0_05"),
        ("tolerance 0.10", {"lengthFeetInches": "6'0", "volumeLitres": "29.20"}, 100, "plus_minus_0_10"),
        ("tolerance 0.20 unique", {"lengthFeetInches": "6'0", "volumeLitres": "29.21"}, 100, "plus_minus_0_20"),
        ("reject over tolerance", {"lengthFeetInches": "6'0", "volumeLitres": "29.31"}, None, None),
        ("reject other length", {"lengthFeetInches": "5'11", "volumeLitres": "29.10"}, None, None),
        ("length only when volume missing", {"lengthFeetInches": "6'0", "volumeLitres": None}, 100, "length_only_no_retailer_volume"),
    ]
    for name, row, expected_id, expected_tolerance in size_cases:
        tests_run += 1
        selected = select_size_candidate(row, 10, sizes)
        actual_id = selected["boardSizeId"] if selected else None
        actual_tolerance = selected["volumeTolerance"] if selected else None
        if actual_id != expected_id or actual_tolerance != expected_tolerance:
            failures.append({
                "case": name,
                "expected": [expected_id, expected_tolerance],
                "actual": [actual_id, actual_tolerance],
            })

    tests_run += 1
    ambiguous_sizes = {
        10: [
            {"boardSizeId": 100, "lengthFeetInches": "6'0", "volumeLitres": Decimal("29.10")},
            {"boardSizeId": 102, "lengthFeetInches": "6'0", "volumeLitres": Decimal("29.30")},
        ]
    }
    if select_size_candidate({"lengthFeetInches": "6'0", "volumeLitres": "29.20"}, 10, ambiguous_sizes):
        failures.append({"case": "reject equally close sizes", "expected": None, "actual": "matched"})

    tests_run += 1
    dimension_sizes = {
        10: [
            {"boardSizeId": 103, "lengthFeetInches": "6'0", "width": "19 1/4", "thickness": "2 7/16", "volumeLitres": Decimal("29.10"), "construction": "PU"},
            {"boardSizeId": 104, "lengthFeetInches": "6'0", "width": "19.25", "thickness": "2.50", "volumeLitres": Decimal("29.10"), "construction": "EPS"},
        ]
    }
    selected = select_size_candidate(
        {"lengthFeetInches": "6'0", "width": "19.25", "thickness": "2 7/16", "volumeLitres": "29.10", "construction": "PU"},
        10,
        dimension_sizes,
    )
    if not selected or selected["boardSizeId"] != 103:
        failures.append({"case": "dimensions break same-volume tie", "expected": 103, "actual": selected})

    for invalid_region in ("AU", "ID", None):
        tests_run += 1
        try:
            build_apply_rows({
                "importableRowsForApply": [
                    {"regionCode": invalid_region, "priceCurrency": "EUR"}
                ]
            })
        except RuntimeError:
            pass
        else:
            failures.append({
                "case": f"EU guard rejects {invalid_region!r}",
                "expected": "RuntimeError",
                "actual": "accepted",
            })
    return {
        "testsRun": tests_run,
        "testsPassed": tests_run - len(failures),
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
            raise RuntimeError(
                "EU apply safety failed: every row must have RegionCode 'EU' and PriceCurrency 'EUR'."
            )
        rows.append(row)
    return rows


def apply_to_sql(report: dict, output_file: Path) -> dict:
    assert_apply_safety(report)
    rows = build_apply_rows(report)
    engine = build_engine()
    apply_counts = Counter()

    with begin_with_retry(engine) as conn:
        assert_schema(conn)
        before = {
            "euInventoryRows": count_inventory_by_region(conn, "EU"),
            "euRetailers": count_retailers_by_region(conn, "EU"),
            "auInventoryRows": count_inventory_by_region(conn, "AU"),
            "idInventoryRows": count_inventory_by_region(conn, "ID"),
        }
        retailer_counts_before = priority_retailer_counts(conn)
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
        brand_links_applied = apply_brand_links(conn, link_report_before["brandUpdates"])
        model_links_applied = apply_model_links(conn, link_report_before["modelUpdates"])
        size_links_applied = apply_size_links(conn, link_report_before["sizeUpdates"])
        apply_counts["brandLinksApplied"] = brand_links_applied
        apply_counts["modelLinksApplied"] = model_links_applied
        apply_counts["sizeLinksApplied"] = size_links_applied
        link_report_after = build_canonical_link_report(conn)

        after = {
            "euInventoryRows": count_inventory_by_region(conn, "EU"),
            "euRetailers": count_retailers_by_region(conn, "EU"),
            "auInventoryRows": count_inventory_by_region(conn, "AU"),
            "idInventoryRows": count_inventory_by_region(conn, "ID"),
        }
        retailer_counts_after = priority_retailer_counts(conn)
        if after["auInventoryRows"] != before["auInventoryRows"]:
            raise RuntimeError(
                "EU import safety failed: AU inventory count changed; transaction rolled back."
            )
        if after["idInventoryRows"] != before["idInventoryRows"]:
            raise RuntimeError(
                "EU import safety failed: ID inventory count changed; transaction rolled back."
            )
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
        "retailerCountsBefore": retailer_counts_before,
        "retailerCountsAfter": retailer_counts_after,
        "validation": validation,
        "canonicalLinkingBeforeApply": public_link_report(link_report_before),
        "canonicalLinkingAfterApply": public_link_report(link_report_after),
        "sampleEuRows": samples,
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(apply_report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_link_report(link_report_after)
    return apply_report


def apply_eu_canonical_links(output_file: Path = LINK_APPLY_REPORT_FILE) -> dict:
    engine = build_engine()
    with begin_with_retry(engine) as conn:
        assert_schema(conn)
        before_counts = {
            region: count_inventory_by_region(conn, region)
            for region in ("AU", "ID", "EU")
        }
        retailer_counts_before = priority_retailer_counts(conn)
        before_report = build_canonical_link_report(conn)

        brand_links = apply_brand_links(conn, before_report["brandUpdates"])
        model_links = apply_model_links(conn, before_report["modelUpdates"])
        size_links = apply_size_links(conn, before_report["sizeUpdates"])

        after_counts = {
            region: count_inventory_by_region(conn, region)
            for region in ("AU", "ID", "EU")
        }
        if after_counts["AU"] != before_counts["AU"]:
            raise RuntimeError(
                "EU link safety failed: AU count changed; transaction rolled back."
            )
        if after_counts["ID"] != before_counts["ID"]:
            raise RuntimeError(
                "EU link safety failed: ID count changed; transaction rolled back."
            )
        if after_counts["EU"] != before_counts["EU"]:
            raise RuntimeError(
                "EU link safety failed: EU row count changed; transaction rolled back."
            )

        retailer_counts_after = priority_retailer_counts(conn)
        before_totals = {
            (row["regionCode"], row["retailerName"]): row["inventoryRows"]
            for row in retailer_counts_before
        }
        after_totals = {
            (row["regionCode"], row["retailerName"]): row["inventoryRows"]
            for row in retailer_counts_after
        }
        if before_totals != after_totals:
            raise RuntimeError(
                "EU link safety failed: priority retailer row counts changed; transaction rolled back."
            )

        after_report = build_canonical_link_report(conn)

    result = {
        "mode": "eu_canonical_link_apply",
        "regionCode": REGION_CODE,
        "beforeCounts": before_counts,
        "afterCounts": after_counts,
        "retailerCountsBefore": retailer_counts_before,
        "retailerCountsAfter": retailer_counts_after,
        "applied": {
            "brandLinks": brand_links,
            "modelLinks": model_links,
            "sizeLinks": size_links,
        },
        "beforeLinkAudit": public_link_report(before_report),
        "afterLinkAudit": public_link_report(after_report),
        "validation": {
            "auCountUnchanged": True,
            "idCountUnchanged": True,
            "euCountUnchanged": True,
            "priorityRetailerCountsUnchanged": True,
            "allWritesRegionCode": REGION_CODE,
            "deletes": 0,
            "truncates": 0,
        },
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_link_report(after_report)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="EU retailer inventory importer. Dry-run by default.")
    parser.add_argument("--input", default=str(INPUT_FILE), help="Normalised EU inventory JSON input.")
    parser.add_argument("--output", default=str(OUTPUT_FILE), help="Dry-run report output path.")
    parser.add_argument("--apply-output", default=str(APPLY_OUTPUT_FILE), help="Apply report output path.")
    parser.add_argument("--retailer", default="", help="Optional retailerSlug filter.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply idempotent EU-only upserts after region and protected-count checks.",
    )
    parser.add_argument("--schema-check", action="store_true", help="Disabled locally; schema checks must run remotely.")
    parser.add_argument("--link-tests", action="store_true", help="Run local canonical model matching tests.")
    parser.add_argument(
        "--apply-links",
        action="store_true",
        help="Apply EU-only brand/model/size links without changing inventory rows.",
    )
    parser.add_argument(
        "--link-apply-output",
        default=str(LINK_APPLY_REPORT_FILE),
        help="Apply report path for --apply-links.",
    )
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

    if args.apply_links:
        link_result = apply_eu_canonical_links(Path(args.link_apply_output))
        before = link_result["beforeLinkAudit"]
        after = link_result["afterLinkAudit"]
        print("EU canonical link apply complete")
        print(f"Before: models={before['linkedModels']} sizes={before['linkedSizes']}")
        print(f"After: models={after['linkedModels']} sizes={after['linkedSizes']}")
        print(f"Applied: {link_result['applied']}")
        print(f"Region counts: {link_result['afterCounts']}")
        print(f"Report: {args.link_apply_output}")
        return

    if args.azure_run:
        print_azure_run_command("scripts/europe/import_eu_retailer_inventory.py --export-sql")
        return

    input_file = Path(args.input)
    output_file = Path(args.output)
    rows = load_input_rows(input_file, args.retailer)
    report = build_report(rows, input_file, args.retailer)

    if args.apply:
        apply_report = apply_to_sql(report, Path(args.apply_output))
        print("EU retailer inventory apply complete")
        print(f"Before region counts: {apply_report['beforeCounts']}")
        print(f"After region counts: {apply_report['afterCounts']}")
        print(f"Before retailer counts: {apply_report['retailerCountsBefore']}")
        print(f"After retailer counts: {apply_report['retailerCountsAfter']}")
        linking = apply_report["canonicalLinkingAfterApply"]
        print(f"Linked BoardModelId rows: {linking['linkedModels']}")
        print(f"Linked BoardSizeId rows: {linking['linkedSizes']}")
        print(f"Apply report: {args.apply_output}")
        return

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
