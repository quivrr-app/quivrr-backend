import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from urllib.parse import quote_plus
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError

from auth.entra_external_id import (
    AuthConfigurationError,
    AuthValidationError,
    get_current_user_optional,
    is_configured as entra_auth_is_configured,
    missing_config_keys as entra_missing_config_keys,
    require_current_user,
)
from observability.operations_dashboard import DASHBOARD_VERSION, build_operations_dashboard_metrics
from utils.retailer_matching import classify_retailer_exact
from utils.dimensions import dimensions_from_title


load_dotenv()


def env_int(name: str, default: int) -> int:

    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value.strip())
    except ValueError:
        return default


def env_bool(name: str, default: bool) -> bool:

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: float) -> float:

    value = os.getenv(name)

    if value is None:
        return default

    try:
        return float(value.strip())
    except ValueError:
        return default


def build_connection_string() -> str:

    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")
    driver = os.getenv(
        "SQL_DRIVER",
        "ODBC Driver 18 for SQL Server"
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

    return (
        "mssql+pyodbc:///?odbc_connect="
        + quote_plus(odbc_string)
    )


engine = create_engine(
    build_connection_string(),
    pool_pre_ping=True,
    pool_recycle=120,
    pool_size=5,
    max_overflow=10
)


OPS_DASHBOARD_API_KEY = os.getenv("OPS_DASHBOARD_API_KEY", "").strip()
OPS_DASHBOARD_CACHE_TTL_SECONDS = env_int("OPS_DASHBOARD_CACHE_TTL_SECONDS", 300)
OPS_DASHBOARD_CACHE_FILE = Path(
    os.getenv(
        "OPS_DASHBOARD_CACHE_FILE",
        str(Path(os.getenv("HOME", ".")) / "data" / "ops_dashboard_metrics_cache.json"),
    )
)
OPS_DASHBOARD_BOOTSTRAP_FILE = Path(
    os.getenv(
        "OPS_DASHBOARD_BOOTSTRAP_FILE",
        str(Path(__file__).resolve().parent / "config" / "ops_dashboard_bootstrap.json"),
    )
)
OPS_DASHBOARD_REFRESH_LOCK_FILE = Path(
    os.getenv(
        "OPS_DASHBOARD_REFRESH_LOCK_FILE",
        str(OPS_DASHBOARD_CACHE_FILE.with_suffix(".lock")),
    )
)
OPS_DASHBOARD_REFRESH_LOCK_TIMEOUT_SECONDS = env_int(
    "OPS_DASHBOARD_REFRESH_LOCK_TIMEOUT_SECONDS",
    900,
)
OPS_DASHBOARD_ALLOW_SYNC_BUILD = env_bool(
    "OPS_DASHBOARD_ALLOW_SYNC_BUILD",
    True,
)
OPS_DASHBOARD_PREWARM_ON_STARTUP = env_bool(
    "OPS_DASHBOARD_PREWARM_ON_STARTUP",
    bool(os.getenv("WEBSITE_INSTANCE_ID")),
)
SEARCH_VERSION = "search_timeout_fix_v2_thin_fallback_v1_broader_brand_fallback_exact_gate_sprint6_1_legacy_brand_rows"
SUPPORTED_CATALOGUE_BRANDS = {
    "Album",
    "Channel Islands",
    "Chemistry Surfboards",
    "Chilli",
    "Christenson",
    "DHD",
    "Firewire",
    "Haydenshapes",
    "JS Industries",
    "Lost",
    "Misfit Shapes",
    "Pyzel",
    "Rusty",
    "Sharp Eye",
    "Simon Anderson",
}
OTHER_MODEL_MATCHES_ENABLED = env_bool("OTHER_MODEL_MATCHES_ENABLED", True)
OTHER_MODEL_MATCHES_LIMIT = env_int("OTHER_MODEL_MATCHES_LIMIT", 6)
OTHER_MODEL_MATCHES_TIMEOUT_SECONDS = env_float("OTHER_MODEL_MATCHES_TIMEOUT_SECONDS", 1.5)
OTHER_MODEL_MATCHES_BUDGET_MS = env_int("OTHER_MODEL_MATCHES_BUDGET_MS", 1500)
_ops_dashboard_cache_lock = Lock()
_ops_dashboard_cache = {
    "generated_at": 0.0,
    "payload": None,
    "loaded_from_disk": False,
    "refresh_in_progress": False,
}


app = FastAPI(
    title="Quivrr API",
    version="1.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def execute_with_retry(query, params=None, attempts=3, timeout_seconds=None):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                if timeout_seconds is not None:
                    connection = connection.execution_options(timeout=timeout_seconds)
                return list(
                    connection.execute(
                        query,
                        params or {}
                    )
                )

        except (OperationalError, DBAPIError) as exc:
            last_error = exc

            if attempt == attempts:
                raise

            time.sleep(0.4 * attempt)

    raise last_error


def fetch_one_with_retry(query, params=None, attempts=3, timeout_seconds=None):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                if timeout_seconds is not None:
                    connection = connection.execution_options(timeout=timeout_seconds)
                return connection.execute(
                    query,
                    params or {}
                ).fetchone()

        except (OperationalError, DBAPIError) as exc:
            last_error = exc

            if attempt == attempts:
                raise

            time.sleep(0.4 * attempt)

    raise last_error


def clean_text(value):

    if value is None:
        return ""

    text_value = str(value).lower()
    text_value = text_value.replace("’", "'")
    text_value = text_value.replace("‘", "'")
    text_value = text_value.replace('"', "")
    text_value = re.sub(r"[^a-z0-9']+", " ", text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()

    return text_value


def model_family_name(model_name):

    model = clean_text(model_name)

    if not model:
        return ""

    if model.startswith("the "):
        model = model[4:]

    parts = model.split()

    descriptive_suffixes = {
        "round",
        "squash",
        "swallow",
        "tail",
        "grom",
        "king",
        "fish",
        "long",
        "toe",
        "step",
        "up",
        "gun",
        "xl",
        "eps",
        "pu",
        "softboard",
        "soft",
        "futureflex",
        "futures",
        "fcs",
        "carbon",
        "wrap",
    }

    while len(parts) > 1 and parts[-1] in descriptive_suffixes:
        parts.pop()

    return " ".join(parts)


def text_contains_phrase(title, normalised_title, phrase):

    cleaned_phrase = clean_text(phrase)

    if not cleaned_phrase:
        return False

    combined_title = clean_text(
        f"{title or ''} {normalised_title or ''}"
    )

    pattern = (
        rf"(?<![a-z0-9])"
        rf"{re.escape(cleaned_phrase)}"
        rf"(?![a-z0-9])"
    )

    return re.search(pattern, combined_title) is not None


def model_family_matches(title, normalised_title, model_name):

    family_name = model_family_name(model_name)

    return text_contains_phrase(
        title,
        normalised_title,
        family_name
    )


def model_name_matches(title, normalised_title, model_name):

    if text_contains_phrase(
        title,
        normalised_title,
        model_name
    ):
        return True

    return model_family_matches(
        title,
        normalised_title,
        model_name
    )


def title_has_length(title, normalised_title, length):

    if not length:
        return False

    combined_title = clean_text(
        f"{title or ''} {normalised_title or ''}"
    )

    normalised_length = clean_text(length)

    return normalised_length in combined_title


def length_to_inches(length):

    if not length:
        return None

    match = re.search(
        r"(?P<feet>\d+)'\s*(?P<inches>\d+)?",
        str(length)
    )

    if not match:
        return None

    feet = int(match.group("feet"))
    inches = int(match.group("inches") or 0)

    return feet * 12 + inches


def format_volume(value):

    if value is None:
        return None

    return float(value)


def format_size_label(row):

    volume = format_volume(row.VolumeLitres)

    base_label = (
        f"{row.LengthFeetInches} x "
        f"{row.Width} x "
        f"{row.Thickness}"
    )

    if volume is None:
        return base_label

    return f"{base_label} | {volume:g}L"


def format_price(value):

    if value is None:
        return None

    return float(value)


def retailer_result(row, result_type):

    result = {
        "resultType": result_type,
        "inventoryId": row.InventoryId,
        "retailerName": row.RetailerName,
        "websiteUrl": row.WebsiteUrl,
        "retailerLogoUrl": row.LogoUrl,
        "title": row.RawProductTitle,
        "productUrl": row.ProductUrl,
        "imageUrl": row.ProductImageUrl,
        "priceAud": format_price(row.PriceAud),
        "priceAmount": format_price(row.PriceAmount) if hasattr(row, "PriceAmount") else None,
        "priceCurrency": row.PriceCurrency if hasattr(row, "PriceCurrency") else None,
        "stockStatus": row.StockStatus,
        "construction": row.Construction,
        "finSetup": row.FinSetup,
        "length": row.LengthFeetInches,
        "width": row.Width,
        "thickness": row.Thickness,
        "volumeLitres": format_volume(
            row.VolumeLitres
        )
    }

    if hasattr(row, "MatchScore"):
        result["matchScore"] = int(row.MatchScore)

    if hasattr(row, "VolumeDelta"):
        result["volumeDelta"] = (
            float(row.VolumeDelta)
            if row.VolumeDelta is not None
            else None
        )

    if hasattr(row, "LengthDelta"):
        result["lengthDelta"] = (
            int(row.LengthDelta)
            if row.LengthDelta is not None
            else None
        )

    return result


def retailer_row_matches_selected_exactly(row, official):

    if getattr(row, "BoardSizeId", None) is not None and row.BoardSizeId == official.BoardSizeId:
        return True

    title = (
        f"{getattr(row, 'RawProductTitle', '') or ''} "
        f"{getattr(row, 'NormalisedProductTitle', '') or ''}"
    )
    parsed_title_dimensions = dimensions_from_title(title)
    strong_model_title = text_contains_phrase(
        getattr(row, "RawProductTitle", None),
        getattr(row, "NormalisedProductTitle", None),
        official.ModelName,
    )

    exact, _reason = classify_retailer_exact(
        {
            "boardSizeId": getattr(row, "BoardSizeId", None),
            "title": title,
            "length": parsed_title_dimensions.get("length") or getattr(row, "LengthFeetInches", None),
            "width": parsed_title_dimensions.get("width") or getattr(row, "Width", None),
            "thickness": parsed_title_dimensions.get("thickness") or getattr(row, "Thickness", None),
            "volume": parsed_title_dimensions.get("volume") or getattr(row, "VolumeLitres", None),
            "construction": getattr(row, "Construction", None),
        },
        {
            "boardSizeId": official.BoardSizeId,
            "length": official.LengthFeetInches,
            "width": official.Width,
            "thickness": official.Thickness,
            "volume": official.VolumeLitres,
            "construction": official.Construction,
        },
        brand_matches=(getattr(row, "BrandId", None) == official.BrandId),
        model_matches=(
            getattr(row, "BoardModelId", None) == official.BoardModelId
            or strong_model_title
        ),
        strong_model_title=strong_model_title,
    )

    return exact


def should_exclude_close_retailer_row(row, official, exact_inventory_ids):

    if getattr(row, "InventoryId", None) in exact_inventory_ids:
        return True

    return retailer_row_matches_selected_exactly(row, official)


def exact_match_count(exact_matches):

    return len(exact_matches)


def close_match_count(close_matches):

    return len(close_matches)


def should_include_other_model_matches(official_brand_name, direct_matches, exact_matches, close_matches):

    return (
        official_brand_name in SUPPORTED_CATALOGUE_BRANDS
        and not direct_matches
        and exact_match_count(exact_matches) == 0
        and close_match_count(close_matches) < 3
    )


def should_run_other_model_matches(direct_matches, exact_matches, close_matches):

    return (
        OTHER_MODEL_MATCHES_ENABLED
        and not direct_matches
        and exact_match_count(exact_matches) == 0
        and close_match_count(close_matches) < 3
        and OTHER_MODEL_MATCHES_LIMIT > 0
    )


def should_skip_other_model_matches_for_budget(elapsed_ms):

    return elapsed_ms >= OTHER_MODEL_MATCHES_BUDGET_MS


def configured_other_model_matches_limit():

    return max(0, min(OTHER_MODEL_MATCHES_LIMIT, 8))


def search_log(event, **fields):

    payload = {
        "event": event,
        "service": "quivrr-api",
        "searchVersion": SEARCH_VERSION,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    payload.update(fields)
    print(json.dumps(payload, default=str), flush=True)


def is_timeout_error(exc):

    message = str(exc).lower()
    return "timeout" in message or "timed out" in message


def ops_dashboard_log(event, **fields):

    payload = {
        "event": event,
        "service": "quivrr-api",
        "dashboardVersion": DASHBOARD_VERSION,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    payload.update(fields)
    print(json.dumps(payload, default=str), flush=True)


def extract_ops_dashboard_key(
    authorization: str | None,
    x_ops_dashboard_key: str | None,
):
    if x_ops_dashboard_key:
        return x_ops_dashboard_key.strip()
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return token.strip()
    return ""


def build_ops_dashboard_response(cache_status: str):
    metrics = build_operations_dashboard_metrics()
    response = {
        "generatedAtUtc": metrics.get("generatedAtUtc"),
        "service": metrics.get("service"),
        "version": metrics.get("version", DASHBOARD_VERSION),
        "regions": metrics.get("regions", []),
        "regionOverview": metrics.get("regionOverview", []),
        "mfaHealth": metrics.get("mfaHealth", []),
        "retailerHealth": metrics.get("retailerHealth", []),
        "retailerHealthByRegion": metrics.get("retailerHealthByRegion", {}),
        "jobHealth": metrics.get("jobHealth", []),
        "jobHealthByRegion": metrics.get("jobHealthByRegion", {}),
        "jobContracts": metrics.get("jobContracts", []),
        "jobContractsByRegion": metrics.get("jobContractsByRegion", {}),
        "inventoryCounts": metrics.get("inventoryCounts", []),
        "searchQuality": metrics.get("searchQuality", []),
        "coverageGaps": metrics.get("coverageGaps", []),
        "canonicalCompleteness": metrics.get("canonicalCompleteness", {}),
        "regionalReadiness": metrics.get("regionalReadiness", []),
        "pipelineHealth": metrics.get("pipelineHealth", []),
        "alerts": metrics.get("alerts", metrics.get("alertSummary", [])),
        "alertSummary": metrics.get("alertSummary", {}),
        "regionDetails": metrics.get("regionDetails", {}),
        "linkQuality": {
            "global": metrics.get("linkQuality", {}).get("global", {}),
            "regionBreakdown": metrics.get("linkQuality", {}).get("regionBreakdown", []),
            "supportedBrands": metrics.get("linkQuality", {}).get("supportedBrands", []),
        },
        "cacheStatus": cache_status,
    }
    ops_dashboard_log(
        "ops_dashboard_response_built",
        cacheStatus=cache_status,
        regionCount=len(response["regions"]),
        alertCount=len(response["alerts"]),
        mfaHealthCount=len(response["mfaHealth"]),
        retailerHealthCount=len(response["retailerHealth"]),
        retailerRegionCount=len(response["retailerHealthByRegion"]),
        jobHealthCount=len(response["jobHealth"]),
        jobHealthRegionCount=len(response["jobHealthByRegion"]),
        jobContractCount=len(response["jobContracts"]),
        jobContractRegionCount=len(response["jobContractsByRegion"]),
    )
    return response


def build_ops_dashboard_warming_response(cache_status: str, refresh_started: bool):

    generated_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    regions = ["AU", "EU", "ID", "US"]
    region_overview = []
    region_details = {}

    for region in regions:
        overview = {
            "region": region,
            "displayName": region,
            "operationalHealthStatus": "grey",
            "dataFreshnessStatus": "grey",
            "dataQualityStatus": "grey",
            "searchHealthStatus": "grey",
            "coverageQualityStatus": "grey",
            "retailerStatus": "grey",
            "mfaStatus": "grey",
            "supportedModelLinkagePct": None,
            "coverageGapPct": None,
            "retailerRuntime": "warming",
            "lastRetailerInventoryRefreshUtc": None,
            "lastMfaRefreshUtc": None,
        }
        region_overview.append(overview)
        region_details[region] = {
            "overview": overview,
            "searchQuality": {
                "supportedModelLinkagePct": None,
                "canonicalSizeFamilyLinkagePct": None,
                "exactBoardSizeLinkagePct": None,
            },
            "coverageGaps": {
                "supportedCanonicalModelsNoStockAnywherePct": None,
                "supportedCanonicalModelsNoStockAnywhere": {"count": None},
                "supportedCanonicalModelsNoActiveRetailerStock": {"count": None},
                "supportedCanonicalModelsNoActiveMfaStock": {"count": None},
                "supportedModelCount": None,
            },
            "retailerHealth": {
                "summary": {
                    "configuredRetailers": None,
                    "healthyRetailers": None,
                    "staleRetailers": None,
                    "failingRetailers": None,
                    "activeRows": None,
                    "availableRows": None,
                    "averageModelLinkagePct": None,
                    "retailerRuntime": "warming",
                },
                "retailers": [],
            },
            "jobHealth": {
                "summary": {
                    "configuredJobs": None,
                    "healthy": None,
                    "yellow": None,
                    "red": None,
                    "lastSuccessfulJobUtc": None,
                },
                "jobs": [],
            },
            "jobContracts": [],
            "alerts": [],
            "mfaHealth": [],
        }

    response = {
        "generatedAtUtc": generated_at_utc,
        "service": "operations_dashboard",
        "version": DASHBOARD_VERSION,
        "regions": regions,
        "regionOverview": region_overview,
        "mfaHealth": [],
        "retailerHealth": [],
        "retailerHealthByRegion": {},
        "jobHealth": [],
        "jobHealthByRegion": {},
        "jobContracts": [],
        "jobContractsByRegion": {},
        "inventoryCounts": [],
        "searchQuality": [],
        "coverageGaps": [],
        "canonicalCompleteness": {},
        "regionalReadiness": [],
        "pipelineHealth": [],
        "alerts": [],
        "alertSummary": {
            "summary": {
                "critical": 0,
                "warnings": 0,
                "staleSources": 0,
                "linkageWarnings": 0,
            },
            "allAlerts": [],
        },
        "regionDetails": region_details,
        "linkQuality": {
            "global": {},
            "regionBreakdown": [],
            "supportedBrands": [],
        },
        "cacheStatus": cache_status,
        "warmingUp": True,
        "refreshStarted": refresh_started,
    }
    ops_dashboard_log(
        "ops_dashboard_warming_served",
        cacheStatus=cache_status,
        refreshStarted=refresh_started,
    )
    return response


def _ops_dashboard_payload_is_complete(payload):

    if not isinstance(payload, dict):
        return False

    required_keys = (
        "regions",
        "regionOverview",
        "mfaHealth",
        "retailerHealth",
        "retailerHealthByRegion",
        "jobHealth",
        "jobHealthByRegion",
        "jobContracts",
        "jobContractsByRegion",
        "inventoryCounts",
        "searchQuality",
        "coverageGaps",
        "canonicalCompleteness",
        "regionalReadiness",
        "pipelineHealth",
        "alerts",
        "alertSummary",
        "regionDetails",
        "linkQuality",
    )
    if any(key not in payload for key in required_keys):
        return False

    regions = payload.get("regions") or []
    region_details = payload.get("regionDetails") or {}
    if not regions or not isinstance(region_details, dict):
        return False

    for region in regions:
        if region not in region_details:
            return False

    return True


def _persist_ops_dashboard_cache(payload, generated_at):
    OPS_DASHBOARD_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    OPS_DASHBOARD_CACHE_FILE.write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "payload": payload,
            }
        ),
        encoding="utf-8",
    )
    ops_dashboard_log(
        "ops_dashboard_cache_persisted",
        cacheFile=str(OPS_DASHBOARD_CACHE_FILE),
    )


def _read_ops_dashboard_snapshot(path: Path):

    if not path.exists():
        return None, 0.0

    raw_payload = json.loads(path.read_text(encoding="utf-8"))
    payload = raw_payload.get("payload")
    generated_at = float(raw_payload.get("generated_at", 0.0))

    if payload is None or generated_at <= 0:
        return None, 0.0

    return payload, generated_at


def _try_acquire_ops_dashboard_refresh_file_lock():

    OPS_DASHBOARD_REFRESH_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if OPS_DASHBOARD_REFRESH_LOCK_FILE.exists():
        age_seconds = time.time() - OPS_DASHBOARD_REFRESH_LOCK_FILE.stat().st_mtime
        if age_seconds > OPS_DASHBOARD_REFRESH_LOCK_TIMEOUT_SECONDS:
            try:
                OPS_DASHBOARD_REFRESH_LOCK_FILE.unlink()
                ops_dashboard_log(
                    "ops_dashboard_refresh_lock_stale_removed",
                    lockFile=str(OPS_DASHBOARD_REFRESH_LOCK_FILE),
                    ageSeconds=round(age_seconds, 2),
                )
            except OSError:
                return False
        else:
            return False

    try:
        file_descriptor = os.open(
            str(OPS_DASHBOARD_REFRESH_LOCK_FILE),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                        "pid": os.getpid(),
                    }
                )
            )
        return True
    except FileExistsError:
        return False


def _release_ops_dashboard_refresh_file_lock():

    try:
        OPS_DASHBOARD_REFRESH_LOCK_FILE.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        ops_dashboard_log(
            "ops_dashboard_refresh_lock_release_failed",
            lockFile=str(OPS_DASHBOARD_REFRESH_LOCK_FILE),
            error=str(exc),
        )


def _load_ops_dashboard_cache_from_disk_locked():
    if _ops_dashboard_cache.get("loaded_from_disk"):
        return

    _ops_dashboard_cache["loaded_from_disk"] = True
    for snapshot_path, loaded_event, failed_event in (
        (
            OPS_DASHBOARD_CACHE_FILE,
            "ops_dashboard_cache_loaded",
            "ops_dashboard_cache_load_failed",
        ),
        (
            OPS_DASHBOARD_BOOTSTRAP_FILE,
            "ops_dashboard_bootstrap_loaded",
            "ops_dashboard_bootstrap_load_failed",
        ),
    ):
        try:
            payload, generated_at = _read_ops_dashboard_snapshot(snapshot_path)
            if payload is None or generated_at <= 0:
                continue

            if payload.get("version") != DASHBOARD_VERSION:
                ops_dashboard_log(
                    "ops_dashboard_snapshot_version_mismatch",
                    cacheFile=str(snapshot_path),
                    snapshotVersion=payload.get("version"),
                    expectedVersion=DASHBOARD_VERSION,
                )
                continue

            _ops_dashboard_cache["payload"] = payload
            _ops_dashboard_cache["generated_at"] = generated_at
            ops_dashboard_log(
                loaded_event,
                cacheFile=str(snapshot_path),
            )
            return
        except Exception as exc:
            ops_dashboard_log(
                failed_event,
                cacheFile=str(snapshot_path),
                error=str(exc),
            )


def _store_ops_dashboard_cache(payload, generated_at):
    with _ops_dashboard_cache_lock:
        _ops_dashboard_cache["generated_at"] = generated_at
        _ops_dashboard_cache["payload"] = dict(payload)
        _ops_dashboard_cache["loaded_from_disk"] = True
        _ops_dashboard_cache["refresh_in_progress"] = False
    try:
        _persist_ops_dashboard_cache(payload, generated_at)
    except Exception as exc:
        ops_dashboard_log(
            "ops_dashboard_cache_persist_failed",
            cacheFile=str(OPS_DASHBOARD_CACHE_FILE),
            error=str(exc),
        )


def _build_and_store_ops_dashboard_response(cache_status: str):
    payload = build_ops_dashboard_response(cache_status)
    _store_ops_dashboard_cache(payload, time.time())
    return payload


def _refresh_ops_dashboard_cache_worker():
    try:
        payload = build_ops_dashboard_response("refresh")
        _store_ops_dashboard_cache(payload, time.time())
        ops_dashboard_log(
            "ops_dashboard_cache_refresh_completed",
            cacheFile=str(OPS_DASHBOARD_CACHE_FILE),
        )
    except Exception as exc:
        with _ops_dashboard_cache_lock:
            _ops_dashboard_cache["refresh_in_progress"] = False
        ops_dashboard_log(
            "ops_dashboard_cache_refresh_failed",
            cacheFile=str(OPS_DASHBOARD_CACHE_FILE),
            error=str(exc),
        )
    finally:
        _release_ops_dashboard_refresh_file_lock()


def _start_ops_dashboard_refresh_locked():
    if _ops_dashboard_cache.get("refresh_in_progress"):
        return False

    if not _try_acquire_ops_dashboard_refresh_file_lock():
        ops_dashboard_log(
            "ops_dashboard_refresh_skipped",
            reason="refresh_lock_held",
            lockFile=str(OPS_DASHBOARD_REFRESH_LOCK_FILE),
        )
        return False

    _ops_dashboard_cache["refresh_in_progress"] = True
    Thread(
        target=_refresh_ops_dashboard_cache_worker,
        name="ops-dashboard-refresh",
        daemon=True,
    ).start()
    ops_dashboard_log(
        "ops_dashboard_refresh_started",
        cacheFile=str(OPS_DASHBOARD_CACHE_FILE),
        lockFile=str(OPS_DASHBOARD_REFRESH_LOCK_FILE),
    )
    return True


def get_cached_ops_dashboard_response():
    now_seconds = time.time()
    with _ops_dashboard_cache_lock:
        _load_ops_dashboard_cache_from_disk_locked()
        cached_payload = _ops_dashboard_cache.get("payload")
        cached_generated_at = float(_ops_dashboard_cache.get("generated_at", 0.0))
        if (
            cached_payload is not None
            and OPS_DASHBOARD_CACHE_TTL_SECONDS > 0
            and (now_seconds - cached_generated_at) < OPS_DASHBOARD_CACHE_TTL_SECONDS
        ):
            ops_dashboard_log(
                "ops_dashboard_cache_hit",
                cacheTtlSeconds=OPS_DASHBOARD_CACHE_TTL_SECONDS,
            )
            cached_response = dict(cached_payload)
            cached_response["cacheStatus"] = "hit"
            return cached_response
        if cached_payload is not None:
            stale_response = dict(cached_payload)
        else:
            stale_response = None

    if stale_response is not None:
        try:
            payload = _build_and_store_ops_dashboard_response("refresh")
            ops_dashboard_log(
                "ops_dashboard_cache_stale_rebuilt_sync",
                cacheTtlSeconds=OPS_DASHBOARD_CACHE_TTL_SECONDS,
            )
            return payload
        except Exception as exc:
            with _ops_dashboard_cache_lock:
                started_refresh = _start_ops_dashboard_refresh_locked()
            ops_dashboard_log(
                "ops_dashboard_cache_stale_served",
                cacheTtlSeconds=OPS_DASHBOARD_CACHE_TTL_SECONDS,
                refreshStarted=started_refresh,
                error=str(exc),
            )
            stale_response["cacheStatus"] = "stale"
            return stale_response

    if not OPS_DASHBOARD_ALLOW_SYNC_BUILD and _ops_dashboard_cache.get("payload") is not None:
        with _ops_dashboard_cache_lock:
            started_refresh = _start_ops_dashboard_refresh_locked()
        return build_ops_dashboard_warming_response("warming", started_refresh)

    payload = _build_and_store_ops_dashboard_response("miss")
    ops_dashboard_log(
        "ops_dashboard_cache_miss",
        cacheTtlSeconds=OPS_DASHBOARD_CACHE_TTL_SECONDS,
    )
    return payload


def prewarm_ops_dashboard_cache():

    if not OPS_DASHBOARD_PREWARM_ON_STARTUP:
        return

    with _ops_dashboard_cache_lock:
        _load_ops_dashboard_cache_from_disk_locked()
        if _ops_dashboard_cache.get("payload") is not None:
            ops_dashboard_log(
                "ops_dashboard_prewarm_skipped",
                reason="cache_already_loaded",
            )
            return
        started_refresh = _start_ops_dashboard_refresh_locked()
    ops_dashboard_log(
        "ops_dashboard_prewarm_checked",
        refreshStarted=started_refresh,
    )


@app.get("/")
def root():

    return {
        "status": "online",
        "service": "quivrr-api"
    }


@app.on_event("startup")
def startup_prewarm_ops_dashboard():

    prewarm_ops_dashboard_cache()


@app.get("/api/ops/dashboard")
def get_ops_dashboard(
    authorization: str | None = Header(default=None),
    x_ops_dashboard_key: str | None = Header(default=None),
):

    if not OPS_DASHBOARD_API_KEY:
        ops_dashboard_log("ops_dashboard_disabled", reason="missing_api_key")
        raise HTTPException(
            status_code=503,
            detail="Operations dashboard endpoint is not enabled."
        )

    provided_key = extract_ops_dashboard_key(authorization, x_ops_dashboard_key)
    if provided_key != OPS_DASHBOARD_API_KEY:
        ops_dashboard_log("ops_dashboard_forbidden")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        return get_cached_ops_dashboard_response()
    except Exception as exc:
        ops_dashboard_log(
            "ops_dashboard_failed",
            errorType=type(exc).__name__,
            errorMessage=str(exc),
        )
        raise HTTPException(
            status_code=503,
            detail="Operations dashboard is temporarily unavailable."
        ) from exc


def identity_config_response() -> dict:
    return {
        "service": "my-quivrr-identity",
        "provider": "microsoft_entra_external_id",
        "configured": entra_auth_is_configured(),
        "missingConfig": entra_missing_config_keys(),
    }


def resolve_required_identity_user(authorization: str | None) -> dict:
    if not entra_auth_is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                **identity_config_response(),
                "message": "Entra External ID is not configured for authenticated APIs.",
            },
        )

    try:
        return require_current_user(authorization)
    except AuthConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                **identity_config_response(),
                "message": str(exc),
            },
        ) from exc
    except AuthValidationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def resolve_optional_identity_user(authorization: str | None) -> dict | None:
    if not authorization:
        return None

    try:
        return get_current_user_optional(authorization)
    except (AuthConfigurationError, AuthValidationError):
        return None


def row_to_dict(row) -> dict | None:
    if row is None:
        return None
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    return dict(row)


def normalise_optional_text(value, max_length: int | None = None):
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    if max_length is not None:
        return text_value[:max_length]
    return text_value


def normalise_optional_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalise_optional_float(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def preferred_brands_payload(value):
    if value in (None, ""):
        return None
    if isinstance(value, list):
        brands = [
            normalise_optional_text(item, 128)
            for item in value
            if normalise_optional_text(item, 128)
        ]
        return json.dumps(brands)
    return normalise_optional_text(value)


def parse_preferred_brands(value):
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    return [
        item.strip()
        for item in str(value).split(",")
        if item and item.strip()
    ]


def fetch_identity_bundle(connection, user_id: str) -> dict:
    user_row = row_to_dict(connection.execute(
        text("""
            SELECT
                UserId,
                EntraObjectId,
                Email,
                DisplayName,
                IdentityProvider,
                HomeRegion,
                CreatedUtc,
                LastLoginUtc,
                IsActive
            FROM dbo.Users
            WHERE UserId = :user_id
        """),
        {"user_id": user_id},
    ).fetchone())

    profile_row = row_to_dict(connection.execute(
        text("""
            SELECT
                UserProfileId,
                UserId,
                HeightCm,
                WeightKg,
                Ability,
                CurrentVolumeLitres,
                PreferredVolumeMinLitres,
                PreferredVolumeMaxLitres,
                WaveType,
                WaveSize,
                SurfFrequency,
                PreferredBrands,
                HomeBreak,
                HomeCountry,
                UpdatedUtc
            FROM dbo.UserProfiles
            WHERE UserId = :user_id
        """),
        {"user_id": user_id},
    ).fetchone())

    consent_row = row_to_dict(connection.execute(
        text("""
            SELECT TOP 1
                ConsentVersion,
                MarketingConsent,
                AnalyticsConsent,
                ProductNotificationConsent,
                ConsentCapturedUtc,
                ConsentSource
            FROM dbo.UserConsents
            WHERE UserId = :user_id
            ORDER BY ConsentCapturedUtc DESC
        """),
        {"user_id": user_id},
    ).fetchone())

    return {
        "user": user_row,
        "profile": profile_row,
        "consent": consent_row,
    }


def ensure_identity_user(identity_user: dict) -> dict:
    entra_object_id = normalise_optional_text(identity_user.get("entraObjectId"), 128)
    if not entra_object_id:
        raise AuthValidationError("Access token does not contain an Entra object identifier.")

    email = normalise_optional_text(identity_user.get("email"), 320)
    display_name = normalise_optional_text(identity_user.get("displayName"), 256)
    identity_provider = normalise_optional_text(identity_user.get("identityProvider"), 64) or "entra_external_id"

    try:
        with engine.begin() as connection:
            existing = row_to_dict(connection.execute(
                text("""
                    SELECT UserId
                    FROM dbo.Users
                    WHERE EntraObjectId = :entra_object_id
                """),
                {"entra_object_id": entra_object_id},
            ).fetchone())

            is_new_user = existing is None
            if is_new_user:
                user_id = str(uuid4())
                connection.execute(
                    text("""
                        INSERT INTO dbo.Users (
                            UserId,
                            EntraObjectId,
                            Email,
                            DisplayName,
                            IdentityProvider,
                            LastLoginUtc,
                            IsActive
                        )
                        VALUES (
                            :user_id,
                            :entra_object_id,
                            :email,
                            :display_name,
                            :identity_provider,
                            SYSUTCDATETIME(),
                            1
                        )
                    """),
                    {
                        "user_id": user_id,
                        "entra_object_id": entra_object_id,
                        "email": email,
                        "display_name": display_name,
                        "identity_provider": identity_provider,
                    },
                )
            else:
                user_id = str(existing["UserId"])
                connection.execute(
                    text("""
                        UPDATE dbo.Users
                        SET
                            Email = COALESCE(:email, Email),
                            DisplayName = COALESCE(:display_name, DisplayName),
                            IdentityProvider = :identity_provider,
                            LastLoginUtc = SYSUTCDATETIME(),
                            IsActive = 1
                        WHERE UserId = :user_id
                    """),
                    {
                        "user_id": user_id,
                        "email": email,
                        "display_name": display_name,
                        "identity_provider": identity_provider,
                    },
                )

            connection.execute(
                text("""
                    IF NOT EXISTS (
                        SELECT 1 FROM dbo.UserProfiles WHERE UserId = :user_id
                    )
                    BEGIN
                        INSERT INTO dbo.UserProfiles (UserProfileId, UserId)
                        VALUES (:profile_id, :user_id)
                    END
                """),
                {"user_id": user_id, "profile_id": str(uuid4())},
            )

            connection.execute(
                text("""
                    IF NOT EXISTS (
                        SELECT 1
                        FROM dbo.UserConsents
                        WHERE UserId = :user_id
                          AND ConsentVersion = :consent_version
                    )
                    BEGIN
                        INSERT INTO dbo.UserConsents (
                            UserConsentId,
                            UserId,
                            ConsentVersion,
                            MarketingConsent,
                            AnalyticsConsent,
                            ProductNotificationConsent,
                            ConsentSource
                        )
                        VALUES (
                            :consent_id,
                            :user_id,
                            :consent_version,
                            0,
                            0,
                            0,
                            :consent_source
                        )
                    END
                """),
                {
                    "consent_id": str(uuid4()),
                    "user_id": user_id,
                    "consent_version": "my-quivrr-consent-v1",
                    "consent_source": "automatic_first_login_default",
                },
            )

            bundle = fetch_identity_bundle(connection, user_id)
            bundle["isNewUser"] = is_new_user
            return bundle
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(
            status_code=503,
            detail="My Quivrr identity storage is temporarily unavailable.",
        ) from exc


def profile_is_complete(profile: dict | None) -> bool:
    if not profile:
        return False
    fields = (
        "HeightCm",
        "WeightKg",
        "Ability",
        "CurrentVolumeLitres",
        "PreferredVolumeMinLitres",
        "PreferredVolumeMaxLitres",
        "WaveType",
        "WaveSize",
        "SurfFrequency",
        "PreferredBrands",
        "HomeBreak",
        "HomeCountry",
    )
    return any(profile.get(field) not in (None, "") for field in fields)


def format_board_summary(brand_name, model_name, construction, length, volume_litres):
    summary_parts = [
        brand_name,
        model_name,
        construction,
        length,
        f"{volume_litres}L" if volume_litres not in (None, "") else None,
    ]
    return " | ".join(part for part in summary_parts if part)


def serialise_saved_board(row: dict) -> dict:
    return {
        "savedBoardId": str(row.get("SavedBoardId")) if row.get("SavedBoardId") is not None else None,
        "boardModelId": row.get("BoardModelId"),
        "boardSizeId": row.get("BoardSizeId"),
        "regionCode": row.get("RegionCode"),
        "note": row.get("Notes"),
        "createdUtc": str(row.get("CreatedUtc")) if row.get("CreatedUtc") is not None else None,
        "brandName": row.get("BrandName"),
        "modelName": row.get("ModelName"),
        "construction": row.get("Construction"),
        "length": row.get("LengthFeetInches"),
        "width": row.get("Width"),
        "thickness": row.get("Thickness"),
        "volumeLitres": float(row.get("VolumeLitres")) if row.get("VolumeLitres") is not None else None,
        "title": format_board_summary(
            row.get("BrandName"),
            row.get("ModelName"),
            row.get("Construction"),
            row.get("LengthFeetInches"),
            row.get("VolumeLitres"),
        ),
    }


def serialise_quiver_item(row: dict) -> dict:
    custom_brand = row.get("CustomBrandName")
    custom_model = row.get("CustomModelName")
    brand_name = row.get("BrandName") or custom_brand
    model_name = row.get("ModelName") or custom_model

    return {
        "quiverId": str(row.get("QuiverId")) if row.get("QuiverId") is not None else None,
        "boardModelId": row.get("BoardModelId"),
        "boardSizeId": row.get("BoardSizeId"),
        "nickname": row.get("Nickname"),
        "purchaseYear": row.get("PurchaseYear"),
        "status": row.get("Status"),
        "currentBoard": bool(row.get("CurrentBoard")),
        "notes": row.get("Notes"),
        "brandName": brand_name,
        "modelName": model_name,
        "construction": row.get("Construction") or row.get("CustomConstruction"),
        "length": row.get("LengthFeetInches"),
        "width": row.get("Width"),
        "thickness": row.get("Thickness"),
        "volumeLitres": float(row.get("VolumeLitres")) if row.get("VolumeLitres") is not None else (
            float(row.get("CustomVolumeLitres")) if row.get("CustomVolumeLitres") is not None else None
        ),
        "customBoard": bool(row.get("IsCustomBoard")),
        "customBrandName": custom_brand,
        "customModelName": custom_model,
        "customDimensions": row.get("CustomDimensions"),
        "customConstruction": row.get("CustomConstruction"),
        "customProductUrl": row.get("CustomProductUrl"),
        "customImageUrl": row.get("CustomImageUrl"),
        "createdUtc": str(row.get("CreatedUtc")) if row.get("CreatedUtc") is not None else None,
        "updatedUtc": str(row.get("UpdatedUtc")) if row.get("UpdatedUtc") is not None else None,
        "title": (
            f"{custom_brand or ''} {custom_model or ''}".strip()
            if row.get("IsCustomBoard")
            else format_board_summary(
                row.get("BrandName"),
                row.get("ModelName"),
                row.get("Construction"),
                row.get("LengthFeetInches"),
                row.get("VolumeLitres"),
            )
        ),
    }


def serialise_user_event(row: dict) -> dict:
    payload = row.get("EventPayload")
    parsed_payload = None
    if payload:
        try:
            parsed_payload = json.loads(payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed_payload = {"raw": payload}

    title = (
        format_board_summary(
            row.get("BrandName"),
            row.get("ModelName"),
            None,
            None,
            None,
        )
        or row.get("ManufacturerName")
        or row.get("EventType")
    )

    return {
        "userEventId": row.get("UserEventId"),
        "eventType": row.get("EventType"),
        "regionCode": row.get("RegionCode"),
        "brandName": row.get("BrandName"),
        "modelName": row.get("ModelName"),
        "boardModelId": row.get("BoardModelId"),
        "boardSizeId": row.get("BoardSizeId"),
        "manufacturerName": row.get("ManufacturerName"),
        "createdUtc": str(row.get("CreatedUtc")) if row.get("CreatedUtc") is not None else None,
        "title": title,
        "payload": parsed_payload,
    }


def fetch_saved_boards(connection, user_id: str) -> list[dict]:
    rows = connection.execute(
        text("""
            SELECT
                sb.SavedBoardId,
                sb.BoardModelId,
                sb.BoardSizeId,
                sb.RegionCode,
                sb.Notes,
                sb.CreatedUtc,
                b.BrandName,
                bm.ModelName,
                bs.Construction,
                bs.LengthFeetInches,
                bs.Width,
                bs.Thickness,
                bs.VolumeLitres
            FROM dbo.SavedBoards sb
            LEFT JOIN dbo.BoardSizes bs
                ON sb.BoardSizeId = bs.BoardSizeId
            LEFT JOIN dbo.BoardModels bm
                ON COALESCE(sb.BoardModelId, bs.BoardModelId) = bm.BoardModelId
            LEFT JOIN dbo.Brands b
                ON bm.BrandId = b.BrandId
            WHERE sb.UserId = :user_id
            ORDER BY sb.CreatedUtc DESC
        """),
        {"user_id": user_id},
    ).fetchall()
    return [serialise_saved_board(row_to_dict(row)) for row in rows]


def fetch_user_quiver(connection, user_id: str) -> list[dict]:
    rows = connection.execute(
        text("""
            SELECT
                uq.QuiverId,
                uq.BoardModelId,
                uq.BoardSizeId,
                uq.Nickname,
                uq.PurchaseYear,
                uq.Status,
                uq.CurrentBoard,
                uq.Notes,
                uq.IsCustomBoard,
                uq.CustomBrandName,
                uq.CustomModelName,
                uq.CustomDimensions,
                uq.CustomConstruction,
                uq.CustomVolumeLitres,
                uq.CustomProductUrl,
                uq.CustomImageUrl,
                uq.CreatedUtc,
                uq.UpdatedUtc,
                b.BrandName,
                bm.ModelName,
                bs.Construction,
                bs.LengthFeetInches,
                bs.Width,
                bs.Thickness,
                bs.VolumeLitres
            FROM dbo.UserQuiver uq
            LEFT JOIN dbo.BoardSizes bs
                ON uq.BoardSizeId = bs.BoardSizeId
            LEFT JOIN dbo.BoardModels bm
                ON COALESCE(uq.BoardModelId, bs.BoardModelId) = bm.BoardModelId
            LEFT JOIN dbo.Brands b
                ON bm.BrandId = b.BrandId
            WHERE uq.UserId = :user_id
            ORDER BY
                CASE WHEN uq.CurrentBoard = 1 THEN 0 ELSE 1 END,
                uq.UpdatedUtc DESC,
                uq.CreatedUtc DESC
        """),
        {"user_id": user_id},
    ).fetchall()
    return [serialise_quiver_item(row_to_dict(row)) for row in rows]


def fetch_recent_activity(connection, user_id: str, limit: int = 20) -> list[dict]:
    bounded_limit = min(max(int(limit), 1), 20)
    rows = connection.execute(
        text(f"""
            SELECT TOP {bounded_limit}
                UserEventId,
                EventType,
                RegionCode,
                BrandName,
                ModelName,
                BoardModelId,
                BoardSizeId,
                ManufacturerName,
                EventPayload,
                CreatedUtc
            FROM dbo.UserEvents
            WHERE UserId = :user_id
            ORDER BY CreatedUtc DESC, UserEventId DESC
        """),
        {"user_id": user_id},
    ).fetchall()
    return [serialise_user_event(row_to_dict(row)) for row in rows]


def write_user_event(
    connection,
    *,
    event_type: str,
    user_id: str | None = None,
    anonymous_session_id: str | None = None,
    region_code: str | None = None,
    brand_name: str | None = None,
    model_name: str | None = None,
    board_model_id: int | None = None,
    board_size_id: int | None = None,
    retailer_id: int | None = None,
    manufacturer_name: str | None = None,
    payload: dict | None = None,
):
    connection.execute(
        text("""
            INSERT INTO dbo.UserEvents (
                UserId,
                AnonymousSessionId,
                EventType,
                RegionCode,
                BrandName,
                ModelName,
                BoardModelId,
                BoardSizeId,
                RetailerId,
                ManufacturerName,
                EventPayload
            )
            VALUES (
                :user_id,
                :anonymous_session_id,
                :event_type,
                :region_code,
                :brand_name,
                :model_name,
                :board_model_id,
                :board_size_id,
                :retailer_id,
                :manufacturer_name,
                :event_payload
            )
        """),
        {
            "user_id": user_id,
            "anonymous_session_id": anonymous_session_id,
            "event_type": normalise_optional_text(event_type, 128),
            "region_code": normalise_optional_text(region_code, 16),
            "brand_name": normalise_optional_text(brand_name, 128),
            "model_name": normalise_optional_text(model_name, 256),
            "board_model_id": board_model_id,
            "board_size_id": board_size_id,
            "retailer_id": retailer_id,
            "manufacturer_name": normalise_optional_text(manufacturer_name, 128),
            "event_payload": json.dumps(payload) if payload else None,
        },
    )


def serialise_identity_bundle(bundle: dict) -> dict:
    user = bundle.get("user") or {}
    profile = bundle.get("profile")
    consent = bundle.get("consent")

    return {
        "authenticated": True,
        "isNewUser": bool(bundle.get("isNewUser")),
        "profileComplete": profile_is_complete(profile),
        "user": {
            "userId": str(user.get("UserId")) if user.get("UserId") is not None else None,
            "entraObjectId": user.get("EntraObjectId"),
            "email": user.get("Email"),
            "displayName": user.get("DisplayName"),
            "identityProvider": user.get("IdentityProvider"),
            "homeRegion": user.get("HomeRegion"),
            "createdUtc": str(user.get("CreatedUtc")) if user.get("CreatedUtc") is not None else None,
            "lastLoginUtc": str(user.get("LastLoginUtc")) if user.get("LastLoginUtc") is not None else None,
        },
        "profile": {
            "heightCm": profile.get("HeightCm") if profile else None,
            "weightKg": profile.get("WeightKg") if profile else None,
            "ability": profile.get("Ability") if profile else None,
            "currentVolumeLitres": float(profile.get("CurrentVolumeLitres")) if profile and profile.get("CurrentVolumeLitres") is not None else None,
            "preferredVolumeMinLitres": float(profile.get("PreferredVolumeMinLitres")) if profile and profile.get("PreferredVolumeMinLitres") is not None else None,
            "preferredVolumeMaxLitres": float(profile.get("PreferredVolumeMaxLitres")) if profile and profile.get("PreferredVolumeMaxLitres") is not None else None,
            "waveType": profile.get("WaveType") if profile else None,
            "waveSize": profile.get("WaveSize") if profile else None,
            "surfFrequency": profile.get("SurfFrequency") if profile else None,
            "preferredBrands": parse_preferred_brands(profile.get("PreferredBrands")) if profile else [],
            "homeBreak": profile.get("HomeBreak") if profile else None,
            "homeCountry": profile.get("HomeCountry") if profile else None,
            "updatedUtc": str(profile.get("UpdatedUtc")) if profile and profile.get("UpdatedUtc") is not None else None,
        },
        "consent": {
            "consentVersion": consent.get("ConsentVersion") if consent else None,
            "marketingConsent": bool(consent.get("MarketingConsent")) if consent else False,
            "analyticsConsent": bool(consent.get("AnalyticsConsent")) if consent else False,
            "productNotificationConsent": bool(consent.get("ProductNotificationConsent")) if consent else False,
        },
    }


def resolve_persisted_identity_bundle(authorization: str | None) -> dict:
    user = resolve_required_identity_user(authorization)
    return ensure_identity_user(user)


@app.get("/api/me")
def get_me(authorization: str | None = Header(default=None)):
    bundle = resolve_persisted_identity_bundle(authorization)
    return {
        **serialise_identity_bundle(bundle),
        "identity": identity_config_response(),
    }


@app.get("/api/my-quivrr/profile")
def get_my_quivrr_profile(authorization: str | None = Header(default=None)):
    bundle = resolve_persisted_identity_bundle(authorization)
    user_id = str(bundle["user"]["UserId"])

    try:
        with engine.connect() as connection:
            recent_activity = fetch_recent_activity(connection, user_id)
            saved_boards = fetch_saved_boards(connection, user_id)
            quiver = fetch_user_quiver(connection, user_id)
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(
            status_code=503,
            detail="My Quivrr profile storage is temporarily unavailable.",
        ) from exc

    return {
        **serialise_identity_bundle(bundle),
        "recentActivity": recent_activity,
        "savedBoardsCount": len(saved_boards),
        "quiverCount": len(quiver),
        "currentBoardCount": len([item for item in quiver if item.get("currentBoard")]),
    }


@app.put("/api/my-quivrr/profile")
def put_my_quivrr_profile(
    payload: dict | None = Body(default=None),
    authorization: str | None = Header(default=None),
):
    bundle = resolve_persisted_identity_bundle(authorization)
    user_id = bundle["user"]["UserId"]
    payload = payload or {}
    updates = {
        "display_name": normalise_optional_text(payload.get("displayName"), 256),
        "home_region": normalise_optional_text(payload.get("homeRegion"), 16),
        "height_cm": normalise_optional_int(payload.get("heightCm")),
        "weight_kg": normalise_optional_int(payload.get("weightKg")),
        "ability": normalise_optional_text(payload.get("ability"), 64),
        "current_volume_litres": normalise_optional_float(payload.get("currentVolumeLitres")),
        "preferred_volume_min_litres": normalise_optional_float(payload.get("preferredVolumeMinLitres")),
        "preferred_volume_max_litres": normalise_optional_float(payload.get("preferredVolumeMaxLitres")),
        "wave_type": normalise_optional_text(payload.get("waveType"), 128),
        "wave_size": normalise_optional_text(payload.get("waveSize"), 128),
        "surf_frequency": normalise_optional_text(payload.get("surfFrequency"), 128),
        "preferred_brands": preferred_brands_payload(payload.get("preferredBrands")),
        "home_break": normalise_optional_text(payload.get("homeBreak"), 256),
        "home_country": normalise_optional_text(payload.get("homeCountry"), 128),
    }

    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    UPDATE dbo.Users
                    SET
                        DisplayName = COALESCE(:display_name, DisplayName),
                        HomeRegion = COALESCE(:home_region, HomeRegion)
                    WHERE UserId = :user_id
                """),
                {"user_id": user_id, **updates},
            )
            connection.execute(
                text("""
                    UPDATE dbo.UserProfiles
                    SET
                        HeightCm = :height_cm,
                        WeightKg = :weight_kg,
                        Ability = :ability,
                        CurrentVolumeLitres = :current_volume_litres,
                        PreferredVolumeMinLitres = :preferred_volume_min_litres,
                        PreferredVolumeMaxLitres = :preferred_volume_max_litres,
                        WaveType = :wave_type,
                        WaveSize = :wave_size,
                        SurfFrequency = :surf_frequency,
                        PreferredBrands = :preferred_brands,
                        HomeBreak = :home_break,
                        HomeCountry = :home_country,
                        UpdatedUtc = SYSUTCDATETIME()
                    WHERE UserId = :user_id
                """),
                {"user_id": user_id, **updates},
            )
            write_user_event(
                connection,
                user_id=str(user_id),
                event_type="ProfileUpdated",
                region_code=updates["home_region"],
                payload={"updatedFields": sorted(payload.keys())},
            )
            updated_bundle = fetch_identity_bundle(connection, str(user_id))
            updated_bundle["isNewUser"] = False
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(
            status_code=503,
            detail="My Quivrr profile storage is temporarily unavailable.",
        ) from exc

    return {
        "status": "saved",
        **serialise_identity_bundle(updated_bundle),
    }


@app.post("/api/logout")
def post_logout():
    return {
        "status": "ok",
        "message": "Client session cleared. Entra External ID owns the browser identity session.",
    }


@app.get("/api/my-quivrr/saved-boards")
def get_saved_boards(authorization: str | None = Header(default=None)):
    bundle = resolve_persisted_identity_bundle(authorization)
    user_id = str(bundle["user"]["UserId"])
    try:
        with engine.connect() as connection:
            saved_boards = fetch_saved_boards(connection, user_id)
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Saved boards are temporarily unavailable.",
        ) from exc
    return {"savedBoards": saved_boards, "count": len(saved_boards)}


@app.post("/api/my-quivrr/saved-boards")
def post_saved_board(
    payload: dict | None = Body(default=None),
    authorization: str | None = Header(default=None),
):
    bundle = resolve_persisted_identity_bundle(authorization)
    user_id = str(bundle["user"]["UserId"])
    payload = payload or {}
    board_model_id = payload.get("boardModelId")
    board_size_id = payload.get("boardSizeId")
    region_code = normalise_optional_text(payload.get("regionCode"), 16)
    notes = normalise_optional_text(payload.get("note") or payload.get("notes"))
    if board_model_id is None and board_size_id is None:
        raise HTTPException(status_code=422, detail="boardModelId or boardSizeId is required.")

    try:
        with engine.begin() as connection:
            existing = row_to_dict(connection.execute(
                text("""
                    SELECT TOP 1 SavedBoardId
                    FROM dbo.SavedBoards
                    WHERE UserId = :user_id
                      AND COALESCE(BoardModelId, -1) = COALESCE(:board_model_id, -1)
                      AND COALESCE(BoardSizeId, -1) = COALESCE(:board_size_id, -1)
                      AND COALESCE(RegionCode, '') = COALESCE(:region_code, '')
                """),
                {
                    "user_id": user_id,
                    "board_model_id": board_model_id,
                    "board_size_id": board_size_id,
                    "region_code": region_code,
                },
            ).fetchone())

            if existing:
                connection.execute(
                    text("""
                        UPDATE dbo.SavedBoards
                        SET Notes = :notes
                        WHERE SavedBoardId = :saved_board_id
                    """),
                    {"saved_board_id": existing["SavedBoardId"], "notes": notes},
                )
                saved_board_id = str(existing["SavedBoardId"])
                status = "updated"
            else:
                saved_board_id = str(uuid4())
                connection.execute(
                    text("""
                        INSERT INTO dbo.SavedBoards (
                            SavedBoardId,
                            UserId,
                            BoardModelId,
                            BoardSizeId,
                            RegionCode,
                            Notes
                        )
                        VALUES (
                            :saved_board_id,
                            :user_id,
                            :board_model_id,
                            :board_size_id,
                            :region_code,
                            :notes
                        )
                    """),
                    {
                        "saved_board_id": saved_board_id,
                        "user_id": user_id,
                        "board_model_id": board_model_id,
                        "board_size_id": board_size_id,
                        "region_code": region_code,
                        "notes": notes,
                    },
                )
                status = "saved"

            write_user_event(
                connection,
                user_id=user_id,
                event_type="BoardSaved",
                region_code=region_code,
                board_model_id=board_model_id,
                board_size_id=board_size_id,
                payload={"savedBoardId": saved_board_id},
            )
            saved_boards = fetch_saved_boards(connection, user_id)
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(status_code=503, detail="Saved boards are temporarily unavailable.") from exc

    saved_board = next((item for item in saved_boards if item["savedBoardId"] == saved_board_id), None)
    return {"status": status, "savedBoard": saved_board, "savedBoards": saved_boards}


@app.delete("/api/my-quivrr/saved-boards/{saved_board_id}")
def delete_saved_board(saved_board_id: str, authorization: str | None = Header(default=None)):
    bundle = resolve_persisted_identity_bundle(authorization)
    user_id = str(bundle["user"]["UserId"])
    try:
        with engine.begin() as connection:
            existing = row_to_dict(connection.execute(
                text("""
                    SELECT TOP 1 SavedBoardId, BoardModelId, BoardSizeId, RegionCode
                    FROM dbo.SavedBoards
                    WHERE SavedBoardId = :saved_board_id
                      AND UserId = :user_id
                """),
                {"saved_board_id": saved_board_id, "user_id": user_id},
            ).fetchone())
            if not existing:
                raise HTTPException(status_code=404, detail="Saved board not found.")

            connection.execute(
                text("""
                    DELETE FROM dbo.SavedBoards
                    WHERE SavedBoardId = :saved_board_id
                      AND UserId = :user_id
                """),
                {"saved_board_id": saved_board_id, "user_id": user_id},
            )
            write_user_event(
                connection,
                user_id=user_id,
                event_type="BoardRemoved",
                region_code=existing.get("RegionCode"),
                board_model_id=existing.get("BoardModelId"),
                board_size_id=existing.get("BoardSizeId"),
                payload={"source": "saved_board"},
            )
    except HTTPException:
        raise
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(status_code=503, detail="Saved boards are temporarily unavailable.") from exc

    return {"status": "deleted", "savedBoardId": saved_board_id}


@app.get("/api/my-quivrr/quiver")
def get_quiver(authorization: str | None = Header(default=None)):
    bundle = resolve_persisted_identity_bundle(authorization)
    user_id = str(bundle["user"]["UserId"])
    try:
        with engine.connect() as connection:
            quiver = fetch_user_quiver(connection, user_id)
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(status_code=503, detail="My Quivrr quiver is temporarily unavailable.") from exc
    return {"quiver": quiver, "count": len(quiver)}


@app.post("/api/my-quivrr/quiver")
def post_quiver_item(
    payload: dict | None = Body(default=None),
    authorization: str | None = Header(default=None),
):
    bundle = resolve_persisted_identity_bundle(authorization)
    user_id = str(bundle["user"]["UserId"])
    payload = payload or {}
    quiver_id = normalise_optional_text(payload.get("quiverId"))
    board_model_id = payload.get("boardModelId")
    board_size_id = payload.get("boardSizeId")
    is_custom_board = bool(payload.get("customBoard")) or bool(payload.get("customModelName"))
    custom_model_name = normalise_optional_text(payload.get("customModelName"), 256)
    if board_model_id is None and board_size_id is None and not custom_model_name:
        raise HTTPException(status_code=422, detail="Provide a board reference or a custom board.")

    params = {
        "quiver_id": quiver_id or str(uuid4()),
        "user_id": user_id,
        "board_model_id": board_model_id,
        "board_size_id": board_size_id,
        "nickname": normalise_optional_text(payload.get("nickname"), 128),
        "purchase_year": normalise_optional_int(payload.get("purchaseYear")),
        "status": normalise_optional_text(payload.get("status"), 64),
        "current_board": 1 if payload.get("currentBoard") else 0,
        "notes": normalise_optional_text(payload.get("notes")),
        "is_custom_board": 1 if is_custom_board else 0,
        "custom_brand_name": normalise_optional_text(payload.get("customBrandName"), 128),
        "custom_model_name": custom_model_name,
        "custom_dimensions": normalise_optional_text(payload.get("customDimensions"), 128),
        "custom_construction": normalise_optional_text(payload.get("customConstruction"), 128),
        "custom_volume_litres": normalise_optional_float(payload.get("customVolumeLitres")),
        "custom_product_url": normalise_optional_text(payload.get("customProductUrl"), 512),
        "custom_image_url": normalise_optional_text(payload.get("customImageUrl"), 512),
    }

    try:
        with engine.begin() as connection:
            if params["current_board"] == 1:
                connection.execute(
                    text("""
                        UPDATE dbo.UserQuiver
                        SET CurrentBoard = 0, UpdatedUtc = SYSUTCDATETIME()
                        WHERE UserId = :user_id
                    """),
                    {"user_id": user_id},
                )

            existing = row_to_dict(connection.execute(
                text("""
                    SELECT TOP 1 QuiverId
                    FROM dbo.UserQuiver
                    WHERE QuiverId = :quiver_id
                      AND UserId = :user_id
                """),
                {"quiver_id": params["quiver_id"], "user_id": user_id},
            ).fetchone())

            if existing:
                connection.execute(
                    text("""
                        UPDATE dbo.UserQuiver
                        SET
                            BoardModelId = :board_model_id,
                            BoardSizeId = :board_size_id,
                            Nickname = :nickname,
                            PurchaseYear = :purchase_year,
                            Status = :status,
                            CurrentBoard = :current_board,
                            Notes = :notes,
                            IsCustomBoard = :is_custom_board,
                            CustomBrandName = :custom_brand_name,
                            CustomModelName = :custom_model_name,
                            CustomDimensions = :custom_dimensions,
                            CustomConstruction = :custom_construction,
                            CustomVolumeLitres = :custom_volume_litres,
                            CustomProductUrl = :custom_product_url,
                            CustomImageUrl = :custom_image_url,
                            UpdatedUtc = SYSUTCDATETIME()
                        WHERE QuiverId = :quiver_id
                          AND UserId = :user_id
                    """),
                    params,
                )
                status = "updated"
            else:
                connection.execute(
                    text("""
                        INSERT INTO dbo.UserQuiver (
                            QuiverId,
                            UserId,
                            BoardModelId,
                            BoardSizeId,
                            Nickname,
                            PurchaseYear,
                            Status,
                            CurrentBoard,
                            Notes,
                            IsCustomBoard,
                            CustomBrandName,
                            CustomModelName,
                            CustomDimensions,
                            CustomConstruction,
                            CustomVolumeLitres,
                            CustomProductUrl,
                            CustomImageUrl
                        )
                        VALUES (
                            :quiver_id,
                            :user_id,
                            :board_model_id,
                            :board_size_id,
                            :nickname,
                            :purchase_year,
                            :status,
                            :current_board,
                            :notes,
                            :is_custom_board,
                            :custom_brand_name,
                            :custom_model_name,
                            :custom_dimensions,
                            :custom_construction,
                            :custom_volume_litres,
                            :custom_product_url,
                            :custom_image_url
                        )
                    """),
                    params,
                )
                status = "created"

            write_user_event(
                connection,
                user_id=user_id,
                event_type="QuiverUpdated",
                board_model_id=board_model_id,
                board_size_id=board_size_id,
                payload={"quiverId": params["quiver_id"], "status": status, "customBoard": is_custom_board},
            )
            quiver = fetch_user_quiver(connection, user_id)
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(status_code=503, detail="My Quivrr quiver is temporarily unavailable.") from exc

    quiver_item = next((item for item in quiver if item["quiverId"] == params["quiver_id"]), None)
    return {"status": status, "quiverItem": quiver_item, "quiver": quiver}


@app.delete("/api/my-quivrr/quiver/{quiver_id}")
def delete_quiver_item(quiver_id: str, authorization: str | None = Header(default=None)):
    bundle = resolve_persisted_identity_bundle(authorization)
    user_id = str(bundle["user"]["UserId"])
    try:
        with engine.begin() as connection:
            existing = row_to_dict(connection.execute(
                text("""
                    SELECT TOP 1 QuiverId, BoardModelId, BoardSizeId
                    FROM dbo.UserQuiver
                    WHERE QuiverId = :quiver_id
                      AND UserId = :user_id
                """),
                {"quiver_id": quiver_id, "user_id": user_id},
            ).fetchone())
            if not existing:
                raise HTTPException(status_code=404, detail="Quiver item not found.")

            connection.execute(
                text("""
                    DELETE FROM dbo.UserQuiver
                    WHERE QuiverId = :quiver_id
                      AND UserId = :user_id
                """),
                {"quiver_id": quiver_id, "user_id": user_id},
            )
            write_user_event(
                connection,
                user_id=user_id,
                event_type="BoardRemoved",
                board_model_id=existing.get("BoardModelId"),
                board_size_id=existing.get("BoardSizeId"),
                payload={"source": "quiver"},
            )
    except HTTPException:
        raise
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(status_code=503, detail="My Quivrr quiver is temporarily unavailable.") from exc

    return {"status": "deleted", "quiverId": quiver_id}


@app.get("/api/my-quivrr/watchlist")
def get_watchlist(authorization: str | None = Header(default=None)):
    resolve_required_identity_user(authorization)
    return {
        "status": "not_implemented",
        "watchlist": [],
    }


@app.post("/api/my-quivrr/watchlist")
def post_watchlist_item(
    payload: dict | None = Body(default=None),
    authorization: str | None = Header(default=None),
):
    resolve_required_identity_user(authorization)
    payload = payload or {}
    return {
        "status": "accepted_not_persisted",
        "receivedFields": sorted(payload.keys()),
    }


@app.post("/api/events")
def post_user_event(
    payload: dict | None = Body(default=None),
    authorization: str | None = Header(default=None),
):
    payload = payload or {}
    user = resolve_optional_identity_user(authorization)
    anonymous_session_id = payload.get("anonymousSessionId") or payload.get("AnonymousSessionId")

    if not user and not anonymous_session_id:
        raise HTTPException(
            status_code=422,
            detail="AnonymousSessionId is required when no authenticated user is supplied.",
        )

    try:
        with engine.begin() as connection:
            user_id = None
            if user:
                ensured = ensure_identity_user(user)
                user_id = str(ensured["user"]["UserId"])

            write_user_event(
                connection,
                user_id=user_id,
                anonymous_session_id=anonymous_session_id,
                event_type=payload.get("eventType") or payload.get("EventType") or "UnknownEvent",
                region_code=payload.get("regionCode") or payload.get("RegionCode"),
                brand_name=payload.get("brandName") or payload.get("BrandName"),
                model_name=payload.get("modelName") or payload.get("ModelName"),
                board_model_id=payload.get("boardModelId") or payload.get("BoardModelId"),
                board_size_id=payload.get("boardSizeId") or payload.get("BoardSizeId"),
                retailer_id=payload.get("retailerId") or payload.get("RetailerId"),
                manufacturer_name=payload.get("manufacturerName") or payload.get("ManufacturerName"),
                payload=payload,
            )
    except (OperationalError, DBAPIError) as exc:
        raise HTTPException(status_code=503, detail="Event intake is temporarily unavailable.") from exc

    return {
        "status": "persisted",
        "authenticated": user is not None,
        "anonymousSessionId": anonymous_session_id,
        "eventType": payload.get("eventType") or payload.get("EventType"),
    }


@app.get("/api/brands")
def get_brands():

    query = text("""
        SELECT
            BrandId,
            BrandName
        FROM dbo.Brands
        WHERE IsActive = 1
        ORDER BY BrandName
    """)

    results = execute_with_retry(query)

    brands = [
        {
            "brandId": row.BrandId,
            "brandName": row.BrandName
        }
        for row in results
    ]

    return brands


@app.get("/api/models/{brand_id}")
def get_models(brand_id: int):

    query = text("""
        SELECT
            BoardModelId,
            ModelName
        FROM dbo.BoardModels
        WHERE BrandId = :brand_id
        AND IsActive = 1
        ORDER BY ModelName
    """)

    results = execute_with_retry(
        query,
        {
            "brand_id": brand_id
        }
    )

    models = [
        {
            "modelId": row.BoardModelId,
            "modelName": row.ModelName
        }
        for row in results
    ]

    return models


@app.get("/api/constructions/{model_id}")
def get_constructions(model_id: int):

    query = text("""
        SELECT DISTINCT
            Construction
        FROM dbo.BoardSizes
        WHERE BoardModelId = :model_id
        AND Construction IS NOT NULL
        ORDER BY Construction
    """)

    results = execute_with_retry(
        query,
        {
            "model_id": model_id
        }
    )

    constructions = [
        {
            "construction": row.Construction
        }
        for row in results
    ]

    return constructions


@app.get("/api/sizes/{model_id}/{construction}")
def get_sizes(
    model_id: int,
    construction: str
):

    query = text("""
        SELECT
            MIN(BoardSizeId) AS BoardSizeId,
            LengthFeetInches,
            Width,
            Thickness,
            VolumeLitres,
            Construction
        FROM dbo.BoardSizes
        WHERE BoardModelId = :model_id
        AND Construction = :construction
        GROUP BY
            LengthFeetInches,
            Width,
            Thickness,
            VolumeLitres,
            Construction
        ORDER BY
            VolumeLitres,
            LengthFeetInches,
            Width,
            Thickness
    """)

    results = execute_with_retry(
        query,
        {
            "model_id": model_id,
            "construction": construction
        }
    )

    sizes = []

    for row in results:
        volume = format_volume(
            row.VolumeLitres
        )

        sizes.append({
            "boardSizeId": row.BoardSizeId,
            "label": format_size_label(row),
            "length": row.LengthFeetInches,
            "width": row.Width,
            "thickness": row.Thickness,
            "volumeLitres": volume,
            "construction": row.Construction
        })

    return sizes




SUPPORTED_DIRECT_MANUFACTURER_BRANDS = {
    "JS Industries",
    "Channel Islands",
    "Album",
    "Chemistry Surfboards",
    "DHD",
    "Pyzel",
    "Firewire",
    "Lost",
    "Sharp Eye",
    "Haydenshapes",
    "Rusty",
    "Misfit Shapes",
    "Chilli",
}


def manufacturer_search_policy(brand_name):
    brand_name = brand_name or ""

    policies = {
        "JS Industries": {
            "direct_enabled": True,
            "manufacturer_mode": "strict",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": False,
        },
        "Channel Islands": {
            "direct_enabled": True,
            "manufacturer_mode": "strict",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": False,
        },
        "Album": {
            "direct_enabled": True,
            "manufacturer_mode": "relaxed_album",
            "retailer_exact_construction_mode": "relaxed",
            "allow_alternate_manufacturer_construction": False,
        },
        "Chemistry Surfboards": {
            "direct_enabled": True,
            "manufacturer_mode": "relaxed_chemistry",
            "retailer_exact_construction_mode": "relaxed",
            "allow_alternate_manufacturer_construction": True,
        },
        "Chilli": {
            "direct_enabled": True,
            "manufacturer_mode": "strict_chilli",
            "retailer_exact_construction_mode": "relaxed",
            "allow_alternate_manufacturer_construction": False,
        },
        "DHD": {
            "direct_enabled": True,
            "manufacturer_mode": "strict",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": True,
        },
        "Pyzel": {
            "direct_enabled": True,
            "manufacturer_mode": "strict",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": True,
        },
        "Firewire": {
            "direct_enabled": True,
            "manufacturer_mode": "strict",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": True,
        },
        "Lost": {
            "direct_enabled": True,
            "manufacturer_mode": "strict",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": True,
        },
        "Sharp Eye": {
            "direct_enabled": True,
            "manufacturer_mode": "strict_sharpeye",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": False,
        },
        "Haydenshapes": {
            "direct_enabled": True,
            "manufacturer_mode": "strict",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": True,
        },
        "Rusty": {
            "direct_enabled": True,
            "manufacturer_mode": "generic",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": True,
        },
        "Misfit Shapes": {
            "direct_enabled": True,
            "manufacturer_mode": "strict",
            "retailer_exact_construction_mode": "strict",
            "allow_alternate_manufacturer_construction": True,
        },
    }

    return policies.get(
        brand_name,
        {
            "direct_enabled": False,
            "manufacturer_mode": "retailer_only",
            "retailer_exact_construction_mode": "relaxed",
            "allow_alternate_manufacturer_construction": False,
        }
    )


def normalise_construction_key(value):
    value = clean_text(value)

    if not value:
        return ""

    aliases = {
        "hyfi": "hyfi 3 0",
        "hyfi 3": "hyfi 3 0",
        "hyfi 3 0": "hyfi 3 0",
        "carbotune": "carbotune",
        "carbon tune": "carbotune",
        "pu": "pu",
        "pe": "pe",
        "poly": "pu",
        "polyester": "pu",
        "eps": "eps",
        "ect": "ect carbon",
        "ect carbon": "ect carbon",
        "spine tek": "spine tek",
        "spinetek": "spine tek",
        "standard": "standard",
        "i bolic": "i bolic",
        "ibolic": "i bolic",
        "i bolic 2 0": "i bolic",
        "ibolic 2 0": "i bolic",
        "i bolic core with fiberglass lamination": "i bolic",
        "ibolic core with fiberglass lamination": "i bolic",
        "i bolic volcanic": "i bolic volcanic",
        "ibolic volcanic": "i bolic volcanic",
    }

    return aliases.get(value, value)


def constructions_match(left, right):
    return normalise_construction_key(left) == normalise_construction_key(right)


@app.get("/api/search")
def search_inventory(boardSizeId: int, regionCode: str = "AU", region: str | None = None):

    region_code = (region or regionCode or "AU").strip().upper()

    if region_code not in {"AU", "ID", "EU", "US"}:
        region_code = "AU"

    request_started_at = time.perf_counter()
    request_id = f"{boardSizeId}:{int(time.time() * 1000)}"

    def elapsed_ms():

        return round((time.perf_counter() - request_started_at) * 1000, 1)

    official_query = text("""
        SELECT
            bs.BoardSizeId,
            bm.BoardModelId,
            b.BrandId,
            b.BrandName,
            bm.ModelName,
            bm.OfficialProductUrl,
            bs.LengthFeetInches,
            bs.Width,
            bs.Thickness,
            bs.VolumeLitres,
            bs.Construction,
            bs.FinSetup,
            bs.TailShape
        FROM dbo.BoardSizes bs
        INNER JOIN dbo.BoardModels bm
            ON bs.BoardModelId = bm.BoardModelId
        INNER JOIN dbo.Brands b
            ON bm.BrandId = b.BrandId
        WHERE bs.BoardSizeId = :board_size_id
    """)

    manufacturer_direct_query = text("""
        SELECT TOP 20
            mi.ManufacturerInventoryId,
            mi.BrandId,
            mi.BoardModelId,
            mi.BoardSizeId,
            mi.BrandName,
            mi.ModelName,
            mi.ProductUrl,
            mi.ProductImageUrl,
            mi.LengthFeetInches,
            mi.Width,
            mi.Thickness,
            mi.VolumeLitres,
            mi.Construction,
            mi.FinSetup,
            mi.PriceAmount,
            mi.PriceCurrency,
            mi.StockStatus,
            mi.IsAvailable,
            mi.RegionCode,

            CASE
                WHEN mi.BoardSizeId = :board_size_id
                    THEN 0

                WHEN mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND (
                        (
                            mi.VolumeLitres IS NOT NULL
                            AND :volume IS NOT NULL
                            AND ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                        )
                        OR (
                            REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                                REPLACE(REPLACE(:width, '"', ''), ' ', '')
                            AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                                REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                        )
                    )
                    THEN 1

                WHEN mi.BrandName = 'JS Industries'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.05
                    )
                    AND mi.Construction IS NOT NULL
                    AND (
                        LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                        OR (
                            LOWER(LTRIM(RTRIM(mi.Construction))) IN ('hyfi', 'hyfi 3', 'hyfi 3.0', 'hyfi 3 0')
                            AND LOWER(LTRIM(RTRIM(:construction))) IN ('hyfi', 'hyfi 3', 'hyfi 3.0', 'hyfi 3 0')
                        )
                        OR (
                            LOWER(LTRIM(RTRIM(mi.Construction))) IN ('carbotune', 'carbon tune')
                            AND LOWER(LTRIM(RTRIM(:construction))) IN ('carbotune', 'carbon tune')
                        )
                    )
                    THEN 0

                WHEN mi.BrandName = 'Channel Islands'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                    AND mi.Construction IS NOT NULL
                    AND (
                        LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                        OR (
                            LOWER(LTRIM(RTRIM(mi.Construction))) IN ('hyfi', 'hyfi 3', 'hyfi 3.0', 'hyfi 3 0')
                            AND LOWER(LTRIM(RTRIM(:construction))) IN ('hyfi', 'hyfi 3', 'hyfi 3.0', 'hyfi 3 0')
                        )
                        OR (
                            LOWER(LTRIM(RTRIM(mi.Construction))) IN ('carbotune', 'carbon tune')
                            AND LOWER(LTRIM(RTRIM(:construction))) IN ('carbotune', 'carbon tune')
                        )
                    )
                    THEN 1


                WHEN mi.BrandName = 'Chilli'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                    AND (
                        :construction IS NULL
                        OR mi.Construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                        OR (
                            LOWER(LTRIM(RTRIM(mi.Construction))) IN ('pu', 'pu stringer')
                            AND LOWER(LTRIM(RTRIM(:construction))) IN ('pu', 'pu stringer', 'standard')
                        )
                    )
                    THEN 2

                WHEN mi.BrandName = 'Chemistry Surfboards'
                    AND mi.BoardModelId = :board_model_id
                    AND (
                        mi.BoardSizeId = :board_size_id
                        OR (
                            mi.LengthFeetInches = :length
                            AND (
                                :volume IS NULL
                                OR mi.VolumeLitres IS NULL
                                OR ABS(CAST(mi.VolumeLitres AS float) -
                                       CAST(:volume AS float)) <= 1.0
                            )
                        )
                    )
                    THEN 2

                WHEN mi.BrandName = 'Album'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    THEN 2

                WHEN mi.BrandName = 'Haydenshapes'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.15
                    )
                    AND (
                        mi.Construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                    THEN 2

                WHEN mi.BrandName = 'DHD'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                    THEN 2

                WHEN mi.BrandName = 'Pyzel'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.15
                    )
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                    AND LOWER(LTRIM(RTRIM(mi.ModelName))) =
                        LOWER(LTRIM(RTRIM(:model_name)))
                    THEN 2


                WHEN mi.BrandName = 'Firewire'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                        OR (
                            LOWER(REPLACE(REPLACE(LTRIM(RTRIM(mi.Construction)), '-', ' '), '.', ' ')) IN (
                                'i bolic',
                                'ibolic',
                                'i bolic 2 0',
                                'ibolic 2 0',
                                'i bolic core with fiberglass lamination',
                                'ibolic core with fiberglass lamination'
                            )
                            AND LOWER(REPLACE(REPLACE(LTRIM(RTRIM(:construction)), '-', ' '), '.', ' ')) IN (
                                'i bolic',
                                'ibolic',
                                'i bolic 2 0',
                                'ibolic 2 0',
                                'i bolic core with fiberglass lamination',
                                'ibolic core with fiberglass lamination'
                            )
                        )
                    )
                    THEN 2

                WHEN mi.BrandName = 'Lost'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.BoardSizeId = :board_size_id
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                    THEN 2

                WHEN mi.BrandName = 'Sharp Eye'
                    AND mi.BoardModelId = :board_model_id
                    AND (
                        mi.BoardSizeId = :board_size_id
                        OR (
                            mi.LengthFeetInches = :length
                            AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                                REPLACE(REPLACE(:width, '"', ''), ' ', '')
                            AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                                REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                            AND (
                                mi.VolumeLitres IS NULL
                                OR :volume IS NULL
                                OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.15
                            )
                        )
                    )
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                    THEN 2

                WHEN :manufacturer_mode = 'generic'
                    AND mi.BrandId = :brand_id
                    AND mi.LengthFeetInches = :length
                    AND (
                        mi.BoardModelId = :board_model_id
                        OR LOWER(LTRIM(RTRIM(mi.ModelName))) =
                           LOWER(LTRIM(RTRIM(:model_name)))
                        OR LOWER(LTRIM(RTRIM(mi.ModelName))) LIKE
                           LOWER(LTRIM(RTRIM(:model_match)))
                        OR LOWER(LTRIM(RTRIM(:model_name))) LIKE
                           '%' + LOWER(LTRIM(RTRIM(mi.ModelName))) + '%'
                    )
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                    THEN 3

                ELSE 9
            END AS MatchRank

        FROM dbo.ManufacturerInventory mi

        WHERE mi.IsActive = 1
            AND mi.RegionCode = :region_code
            AND mi.AvailabilitySource = 'manufacturer_direct'
            AND mi.BrandId = :brand_id
            AND (
                (
                    mi.BoardSizeId = :board_size_id
                )
                OR
                (
                    mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND (
                        (
                            mi.VolumeLitres IS NOT NULL
                            AND :volume IS NOT NULL
                            AND ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                        )
                        OR (
                            REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                                REPLACE(REPLACE(:width, '"', ''), ' ', '')
                            AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                                REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                        )
                    )
                )
                OR
                (
                    mi.BrandName = 'JS Industries'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.05
                    )
                    AND mi.Construction IS NOT NULL
                    AND (
                        LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                        OR (
                            LOWER(LTRIM(RTRIM(mi.Construction))) IN ('hyfi', 'hyfi 3', 'hyfi 3.0', 'hyfi 3 0')
                            AND LOWER(LTRIM(RTRIM(:construction))) IN ('hyfi', 'hyfi 3', 'hyfi 3.0', 'hyfi 3 0')
                        )
                        OR (
                            LOWER(LTRIM(RTRIM(mi.Construction))) IN ('carbotune', 'carbon tune')
                            AND LOWER(LTRIM(RTRIM(:construction))) IN ('carbotune', 'carbon tune')
                        )
                    )
                )
                OR
                (
                    mi.BrandName = 'Channel Islands'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                    AND mi.Construction IS NOT NULL
                    AND LOWER(LTRIM(RTRIM(mi.Construction))) =
                        LOWER(LTRIM(RTRIM(:construction)))
                )
                OR
                (
                    mi.BrandName = 'Chilli'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                    AND (
                        :construction IS NULL
                        OR mi.Construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                        OR (
                            LOWER(LTRIM(RTRIM(mi.Construction))) IN ('pu', 'pu stringer')
                            AND LOWER(LTRIM(RTRIM(:construction))) IN ('pu', 'pu stringer', 'standard')
                        )
                    )
                )
                OR
                (
                    mi.BrandName = 'Album'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                )
                OR
                (
                    mi.BrandName = 'Haydenshapes'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.15
                    )
                    AND (
                        mi.Construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                )
                OR
                (
                    mi.BrandName = 'DHD'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                )
                OR
                (
                    mi.BrandName = 'Firewire'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                        OR (
                            LOWER(REPLACE(REPLACE(LTRIM(RTRIM(mi.Construction)), '-', ' '), '.', ' ')) IN (
                                'i bolic',
                                'ibolic',
                                'i bolic 2 0',
                                'ibolic 2 0',
                                'i bolic core with fiberglass lamination',
                                'ibolic core with fiberglass lamination'
                            )
                            AND LOWER(REPLACE(REPLACE(LTRIM(RTRIM(:construction)), '-', ' '), '.', ' ')) IN (
                                'i bolic',
                                'ibolic',
                                'i bolic 2 0',
                                'ibolic 2 0',
                                'i bolic core with fiberglass lamination',
                                'ibolic core with fiberglass lamination'
                            )
                        )
                    )
                )

                OR
                (
                    mi.BrandName = 'Lost'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.BoardSizeId = :board_size_id
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                )
                OR
                (
                    mi.BrandName = 'Misfit Shapes'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                )
                OR
                (
                    mi.BrandName = 'Pyzel'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.15
                    )
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                    AND LOWER(LTRIM(RTRIM(mi.ModelName))) =
                        LOWER(LTRIM(RTRIM(:model_name)))
                )
                OR
                (
                    mi.BrandName = 'Sharp Eye'
                    AND mi.BoardModelId = :board_model_id
                    AND (
                        mi.BoardSizeId = :board_size_id
                        OR (
                            mi.LengthFeetInches = :length
                            AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                                REPLACE(REPLACE(:width, '"', ''), ' ', '')
                            AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                                REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                            AND (
                                mi.VolumeLitres IS NULL
                                OR :volume IS NULL
                                OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.15
                            )
                        )
                    )
                    AND (
                        mi.Construction IS NULL
                        OR :construction IS NULL
                        OR LOWER(LTRIM(RTRIM(mi.Construction))) =
                            LOWER(LTRIM(RTRIM(:construction)))
                    )
                )
                OR
                (
                    mi.BrandName = 'Christenson'
                    AND mi.BoardModelId = :board_model_id
                    AND mi.LengthFeetInches = :length
                    AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                )
                OR
                (
                    :manufacturer_mode = 'generic'
                    AND mi.BrandId = :brand_id
                    AND mi.LengthFeetInches = :length
                    AND (
                        mi.BoardModelId = :board_model_id
                        OR LOWER(LTRIM(RTRIM(mi.ModelName))) =
                           LOWER(LTRIM(RTRIM(:model_name)))
                        OR LOWER(LTRIM(RTRIM(mi.ModelName))) LIKE
                           LOWER(LTRIM(RTRIM(:model_match)))
                        OR LOWER(LTRIM(RTRIM(:model_name))) LIKE
                           '%' + LOWER(LTRIM(RTRIM(mi.ModelName))) + '%'
                    )
                    AND (
                        mi.VolumeLitres IS NULL
                        OR :volume IS NULL
                        OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    )
                )
            )

        ORDER BY
            CASE WHEN mi.IsAvailable = 1 THEN 0 ELSE 1 END,
            MatchRank ASC,
            mi.PriceAmount ASC,
            mi.ManufacturerInventoryId ASC
    """)

    alternate_manufacturer_direct_query = text("""
        SELECT TOP 20
            mi.ManufacturerInventoryId,
            mi.BrandId,
            mi.BoardModelId,
            mi.BoardSizeId,
            mi.BrandName,
            mi.ModelName,
            mi.ProductUrl,
            mi.ProductImageUrl,
            mi.LengthFeetInches,
            mi.Width,
            mi.Thickness,
            mi.VolumeLitres,
            mi.Construction,
            mi.FinSetup,
            mi.PriceAmount,
            mi.PriceCurrency,
            mi.StockStatus,
            mi.IsAvailable,
            mi.RegionCode

        FROM dbo.ManufacturerInventory mi

        WHERE :direct_enabled = 1
            AND :allow_alternate_manufacturer_construction = 1
            AND :construction IS NOT NULL
            AND mi.IsActive = 1
            AND mi.RegionCode = :region_code
            AND mi.AvailabilitySource = 'manufacturer_direct'
            AND mi.BrandId = :brand_id
            AND mi.BoardModelId = :board_model_id
            AND mi.LengthFeetInches = :length
            AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                REPLACE(REPLACE(:width, '"', ''), ' ', '')
            AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
            AND mi.BrandName <> 'Pyzel'
            AND (
                mi.Construction IS NULL
                OR LOWER(LTRIM(RTRIM(mi.Construction))) <>
                    LOWER(LTRIM(RTRIM(:construction)))
            )

        ORDER BY
            CASE WHEN mi.IsAvailable = 1 THEN 0 ELSE 1 END,
            mi.PriceAmount ASC,
            mi.ManufacturerInventoryId ASC
    """)

    exact_query = text("""
        SELECT TOP 500
            ri.InventoryId,
            ri.RawProductTitle,
            ri.NormalisedProductTitle,
            ri.ProductUrl,
            ri.ProductImageUrl,
            ri.PriceAud,
            ri.PriceAmount,
            ri.PriceCurrency,
            ri.StockStatus,
            ri.Construction,
            ri.FinSetup,
            ri.LengthFeetInches,
            ri.Width,
            ri.Thickness,
            ri.VolumeLitres,
            ri.BrandId,
            ri.BoardModelId,
            ri.BoardSizeId,
            r.RetailerName,
            r.WebsiteUrl,
            r.LogoUrl,
            CASE
                WHEN ri.VolumeLitres IS NULL THEN NULL
                ELSE ABS(
                    CAST(ri.VolumeLitres AS float)
                    - CAST(:volume AS float)
                )
            END AS VolumeDelta,
            CASE
                WHEN ri.RawProductTitle LIKE :model_match
                    OR ri.NormalisedProductTitle LIKE :model_match
                    THEN 60
                ELSE 35
            END
            +
            CASE
                WHEN ri.Construction IS NOT NULL
                    AND :construction IS NOT NULL
                    AND LOWER(ri.Construction) = LOWER(:construction)
                    THEN 25
                ELSE 0
            END
            +
            CASE
                WHEN ri.FinSetup IS NOT NULL
                    AND :fin_setup IS NOT NULL
                    AND LOWER(ri.FinSetup) = LOWER(:fin_setup)
                    THEN 10
                ELSE 0
            END
            +
            CASE
                WHEN ri.VolumeLitres IS NOT NULL
                    AND ABS(
                        CAST(ri.VolumeLitres AS float)
                        - CAST(:volume AS float)
                    ) <= 0.25
                    THEN 25
                WHEN ri.VolumeLitres IS NOT NULL
                    AND ABS(
                        CAST(ri.VolumeLitres AS float)
                        - CAST(:volume AS float)
                    ) <= 0.75
                    THEN 15
                ELSE 0
            END
            +
            CASE
                WHEN ri.Width IS NOT NULL THEN 5 ELSE 0
            END
            +
            CASE
                WHEN ri.Thickness IS NOT NULL THEN 5 ELSE 0
            END AS MatchScore
        FROM dbo.RetailerInventory ri
        INNER JOIN dbo.Retailers r
            ON ri.RetailerId = r.RetailerId
        WHERE ri.IsActive = 1
        AND ri.RegionCode = :region_code
        AND ri.BrandId = :brand_id
        AND (
            ri.BoardModelId = :board_model_id
            OR (
                ri.BoardModelId IS NULL
                AND (
                    ri.RawProductTitle LIKE :model_match
                    OR ri.NormalisedProductTitle LIKE :model_match
                )
            )
        )
        AND (
            ri.StockStatus IS NULL
            OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN (
                'in stock',
                'instock',
                'in_stock',
                'available',
                'true'
            )
        )
        ORDER BY
            MatchScore DESC,
            CASE
                WHEN ri.VolumeLitres IS NULL THEN 1
                ELSE 0
            END,
            VolumeDelta ASC,
            ri.PriceAud ASC,
            r.RetailerName ASC
    """)

    close_query = text("""
        SELECT TOP 300
            ri.InventoryId,
            ri.RawProductTitle,
            ri.NormalisedProductTitle,
            ri.ProductUrl,
            ri.ProductImageUrl,
            ri.PriceAud,
            ri.PriceAmount,
            ri.PriceCurrency,
            ri.StockStatus,
            ri.Construction,
            ri.FinSetup,
            ri.LengthFeetInches,
            ri.Width,
            ri.Thickness,
            ri.VolumeLitres,
            r.RetailerName,
            r.WebsiteUrl,
            r.LogoUrl,
            CASE
                WHEN ri.VolumeLitres IS NULL THEN NULL
                ELSE ABS(
                    CAST(ri.VolumeLitres AS float)
                    - CAST(:volume AS float)
                )
            END AS VolumeDelta,
            CASE
                WHEN ri.LengthFeetInches IS NULL THEN NULL
                ELSE ABS(
                    CAST(:target_length_inches AS int)
                    - CAST(:target_length_inches AS int)
                )
            END AS LengthDelta,
            CASE
                WHEN ri.RawProductTitle LIKE :model_match
                    OR ri.NormalisedProductTitle LIKE :model_match
                    THEN 70
                WHEN ri.RawProductTitle LIKE :model_match
                    OR ri.NormalisedProductTitle LIKE :model_match
                    THEN 45
                ELSE 0
            END
            +
            CASE
                WHEN ri.LengthFeetInches = :length THEN 25
                WHEN ri.LengthFeetInches IN (:one_down_length, :one_up_length) THEN 15
                WHEN ri.LengthFeetInches IS NULL
                    AND (
                        ri.RawProductTitle LIKE :length_title_match
                        OR ri.NormalisedProductTitle LIKE :length_title_match
                    )
                    THEN 10
                ELSE 0
            END
            +
            CASE
                WHEN ri.Construction IS NOT NULL
                    AND :construction IS NOT NULL
                    AND LOWER(ri.Construction) = LOWER(:construction)
                    THEN 20
                WHEN ri.Construction IS NOT NULL
                    THEN 8
                ELSE 0
            END
            +
            CASE
                WHEN ri.VolumeLitres IS NOT NULL
                    AND ABS(
                        CAST(ri.VolumeLitres AS float)
                        - CAST(:volume AS float)
                    ) <= 0.75
                    THEN 25
                WHEN ri.VolumeLitres IS NOT NULL
                    AND ABS(
                        CAST(ri.VolumeLitres AS float)
                        - CAST(:volume AS float)
                    ) <= 2.0
                    THEN 15
                WHEN ri.VolumeLitres IS NULL
                    THEN 3
                ELSE 0
            END
            +
            CASE
                WHEN ri.Width IS NOT NULL THEN 4 ELSE 0
            END
            +
            CASE
                WHEN ri.Thickness IS NOT NULL THEN 4 ELSE 0
            END AS MatchScore
        FROM dbo.RetailerInventory ri
        INNER JOIN dbo.Retailers r
            ON ri.RetailerId = r.RetailerId
        WHERE ri.IsActive = 1
        AND ri.RegionCode = :region_code
        AND ri.BrandId = :brand_id
        AND (
            ri.StockStatus IS NULL
            OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN (
                'in stock',
                'instock',
                'in_stock',
                'available',
                'true'
            )
        )
        AND (
            ri.RawProductTitle LIKE :model_match
            OR ri.NormalisedProductTitle LIKE :model_match
            OR (
                :region_code = 'ID'
                AND (
                    ri.RawProductTitle LIKE :model_family_match
                    OR ri.NormalisedProductTitle LIKE :model_family_match
                )
            )
        )
        AND (
            :region_code = 'ID'
            OR ri.LengthFeetInches = :length
            OR ri.LengthFeetInches = :one_down_length
            OR ri.LengthFeetInches = :one_up_length
            OR (
                ri.LengthFeetInches IS NULL
                AND (
                    ri.RawProductTitle LIKE :length_title_match
                    OR ri.NormalisedProductTitle LIKE :length_title_match
                )
            )
        )
        AND (
            :region_code = 'ID'
            OR ri.VolumeLitres IS NULL
            OR ABS(
                CAST(ri.VolumeLitres AS float)
                - CAST(:volume AS float)
            ) <= 2.0
        )
        ORDER BY
            MatchScore DESC,
            CASE
                WHEN ri.VolumeLitres IS NULL THEN 1
                ELSE 0
            END,
            VolumeDelta ASC,
            ri.PriceAud ASC,
            r.RetailerName ASC
    """)

    other_models_query = text("""
        SELECT TOP 8
            ri.InventoryId,
            ri.BrandId,
            ri.BoardModelId,
            ri.BoardSizeId,
            ri.RawProductTitle,
            ri.NormalisedProductTitle,
            ri.ProductUrl,
            ri.ProductImageUrl,
            ri.PriceAud,
            ri.PriceAmount,
            ri.PriceCurrency,
            ri.StockStatus,
            ri.Construction,
            ri.FinSetup,
            ri.LengthFeetInches,
            ri.Width,
            ri.Thickness,
            ri.VolumeLitres,
            r.RetailerName,
            r.WebsiteUrl,
            r.LogoUrl,
            bm.ModelName AS CanonicalModelName,
            CASE
                WHEN ri.BoardModelId = :board_model_id THEN 240
                ELSE 0
            END
            +
            CASE
                WHEN ri.Construction IS NOT NULL
                     AND :construction IS NOT NULL
                     AND LOWER(LTRIM(RTRIM(ri.Construction))) =
                         LOWER(LTRIM(RTRIM(:construction)))
                    THEN 80
                ELSE 0
            END
            +
            CASE
                WHEN ri.LengthFeetInches = :length THEN 40
                WHEN ri.LengthFeetInches IN (:one_down_length, :one_up_length) THEN 25
                WHEN ri.LengthFeetInches IN (:two_down_length, :two_up_length) THEN 10
                ELSE 0
            END
            +
            CASE
                WHEN ri.VolumeLitres IS NOT NULL
                     AND :volume IS NOT NULL
                     AND ABS(CAST(ri.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                    THEN 20
                WHEN ri.VolumeLitres IS NOT NULL
                     AND :volume IS NOT NULL
                     AND ABS(CAST(ri.VolumeLitres AS float) - CAST(:volume AS float)) <= 2.0
                    THEN 10
                ELSE 0
            END
            +
            CASE
                WHEN ri.ProductImageUrl IS NOT NULL THEN 8
                ELSE 0
            END
            +
            CASE
                WHEN ri.PriceAmount IS NOT NULL OR ri.PriceAud IS NOT NULL THEN 5
                ELSE 0
            END
            +
            CASE
                WHEN ri.BoardSizeId IS NOT NULL THEN 3
                ELSE 0
            END AS MatchScore
        FROM dbo.RetailerInventory ri
        INNER JOIN dbo.Retailers r
            ON ri.RetailerId = r.RetailerId
        LEFT JOIN dbo.BoardModels bm
            ON bm.BoardModelId = ri.BoardModelId
        WHERE ri.IsActive = 1
          AND ri.RegionCode = :region_code
          AND ri.BrandId = :brand_id
          AND ri.ProductUrl IS NOT NULL
          AND (
                :excluded_inventory_ids_empty = 1
                OR ri.InventoryId NOT IN :excluded_inventory_ids
          )
          AND (
                :board_size_id IS NULL
                OR ri.BoardSizeId IS NULL
                OR ri.BoardSizeId <> :board_size_id
          )
          AND (
                ri.StockStatus IS NULL
                OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN (
                    'in stock',
                    'instock',
                    'in_stock',
                    'available',
                    'true'
                )
          )
        ORDER BY
            MatchScore DESC,
            CASE
                WHEN ri.ProductImageUrl IS NULL THEN 1
                ELSE 0
            END,
            CASE
                WHEN ri.PriceAmount IS NULL AND ri.PriceAud IS NULL THEN 1
                ELSE 0
            END,
            CASE
                WHEN ri.VolumeLitres IS NULL THEN 1
                ELSE 0
            END,
            ri.PriceAud ASC,
            r.RetailerName ASC
    """).bindparams(bindparam("excluded_inventory_ids", expanding=True))

    official = fetch_one_with_retry(
        official_query,
        {
            "board_size_id": boardSizeId
        }
    )

    if not official:
        return {
            "apiBuild": "manufacturer-policy-v1-thin-fallback",
            "searchVersion": SEARCH_VERSION,
            "regionCode": region_code,
            "manufacturer": None,
            "exactRetailerMatches": [],
            "closeRetailerMatches": [],
            "otherModelMatches": []
        }

    policy = manufacturer_search_policy(official.BrandName)

    direct_enabled = 1 if policy.get("direct_enabled") else 0
    manufacturer_mode = policy.get("manufacturer_mode", "retailer_only")
    retailer_exact_construction_strict = (
        1
        if policy.get("retailer_exact_construction_mode") == "strict"
        else 0
    )
    allow_alternate_manufacturer_construction = (
        1
        if policy.get("allow_alternate_manufacturer_construction")
        else 0
    )

    target_length_inches = length_to_inches(
        official.LengthFeetInches
    )

    one_down_length = None
    one_up_length = None
    two_down_length = None
    two_up_length = None

    if target_length_inches is not None:
        one_down_length = (
            f"{target_length_inches // 12}'"
            f"{target_length_inches % 12 - 1}"
        )

        one_up_length = (
            f"{target_length_inches // 12}'"
            f"{target_length_inches % 12 + 1}"
        )

        one_down_inches = target_length_inches - 1
        one_up_inches = target_length_inches + 1

        one_down_length = (
            f"{one_down_inches // 12}'"
            f"{one_down_inches % 12}"
        )

        one_up_length = (
            f"{one_up_inches // 12}'"
            f"{one_up_inches % 12}"
        )

        two_down_inches = target_length_inches - 2
        two_up_inches = target_length_inches + 2

        two_down_length = (
            f"{two_down_inches // 12}'"
            f"{two_down_inches % 12}"
        )

        two_up_length = (
            f"{two_up_inches // 12}'"
            f"{two_up_inches % 12}"
        )

    model_match = f"%{official.ModelName}%"
    model_family_match = f"%{model_family_name(official.ModelName)}%"
    length_title_match = f"%{official.LengthFeetInches}%"

    official_result = {
        "resultType": "manufacturer",
        "brandName": official.BrandName,
        "modelName": official.ModelName,
        "productUrl": official.OfficialProductUrl,
        "label": format_size_label(official),
        "length": official.LengthFeetInches,
        "width": official.Width,
        "thickness": official.Thickness,
        "volumeLitres": format_volume(
            official.VolumeLitres
        ),
        "construction": official.Construction,
        "finSetup": official.FinSetup,
        "tailShape": official.TailShape
    }

    manufacturer_direct_rows = execute_with_retry(
        manufacturer_direct_query,
        {
            "board_size_id": official.BoardSizeId,
            "board_model_id": official.BoardModelId,
            "brand_id": official.BrandId,
            "model_name": official.ModelName,
            "model_match": model_match,
            "length": official.LengthFeetInches,
            "width": official.Width,
            "thickness": official.Thickness,
            "volume": official.VolumeLitres,
            "construction": official.Construction,
            "direct_enabled": direct_enabled,
            "manufacturer_mode": manufacturer_mode,
            "allow_alternate_manufacturer_construction": allow_alternate_manufacturer_construction,
            "region_code": region_code
        }
    )

    alternate_manufacturer_direct_rows = execute_with_retry(
        alternate_manufacturer_direct_query,
        {
            "board_size_id": official.BoardSizeId,
            "board_model_id": official.BoardModelId,
            "brand_id": official.BrandId,
            "length": official.LengthFeetInches,
            "width": official.Width,
            "thickness": official.Thickness,
            "construction": official.Construction,
            "direct_enabled": direct_enabled,
            "manufacturer_mode": manufacturer_mode,
            "allow_alternate_manufacturer_construction": allow_alternate_manufacturer_construction,
            "region_code": region_code
        }
    )

    direct_matches = []

    for row in manufacturer_direct_rows:
        if official.BrandName == "JS Industries" and not constructions_match(row.Construction, official.Construction):
            continue

        direct_matches.append({
            "resultType": "manufacturerDirect",
            "manufacturerInventoryId": row.ManufacturerInventoryId,
            "brandName": row.BrandName,
            "modelName": row.ModelName,
            "productUrl": row.ProductUrl,
            "productImageUrl": row.ProductImageUrl,
            "imageUrl": row.ProductImageUrl,
            "length": row.LengthFeetInches,
            "width": row.Width,
            "thickness": row.Thickness,
            "volumeLitres": format_volume(row.VolumeLitres),
            "construction": row.Construction,
            "finSetup": row.FinSetup,
            "priceAmount": float(row.PriceAmount) if row.PriceAmount is not None else None,
            "priceCurrency": row.PriceCurrency,
            "stockStatus": row.StockStatus,
            "isAvailable": bool(row.IsAvailable),
            "regionCode": row.RegionCode
        })
    alternate_direct_matches = []

    for row in alternate_manufacturer_direct_rows:
        alternate_direct_matches.append({
            "resultType": "manufacturerAlternateConstruction",
            "manufacturerInventoryId": row.ManufacturerInventoryId,
            "brandName": row.BrandName,
            "modelName": row.ModelName,
            "productUrl": row.ProductUrl,
            "productImageUrl": row.ProductImageUrl,
            "imageUrl": row.ProductImageUrl,
            "length": row.LengthFeetInches,
            "width": row.Width,
            "thickness": row.Thickness,
            "volumeLitres": format_volume(row.VolumeLitres),
            "construction": row.Construction,
            "finSetup": row.FinSetup,
            "priceAmount": float(row.PriceAmount) if row.PriceAmount is not None else None,
            "priceCurrency": row.PriceCurrency,
            "stockStatus": row.StockStatus,
            "isAvailable": bool(row.IsAvailable),
            "regionCode": row.RegionCode
        })

    if official.BrandName == "Chemistry Surfboards" and not direct_matches and alternate_direct_matches:
        promoted_matches = []

        for match in alternate_direct_matches:
            promoted = dict(match)
            promoted["resultType"] = "manufacturerDirect"
            promoted_matches.append(promoted)

        direct_matches = promoted_matches

    official_result["directManufacturerMatches"] = direct_matches
    official_result["alternateManufacturerMatches"] = alternate_direct_matches
    official_result["hasDirectManufacturerStock"] = len(direct_matches) > 0

    if direct_matches:
        first_direct = direct_matches[0]
        official_result["resultType"] = "manufacturerDirect"
        official_result["manufacturerAvailability"] = {
            "isAvailable": bool(first_direct.get("isAvailable")),
            "stockStatus": first_direct.get("stockStatus")
        }
        official_result["productUrl"] = first_direct.get("productUrl") or official_result.get("productUrl")
        official_result["productImageUrl"] = first_direct.get("productImageUrl")
        official_result["imageUrl"] = first_direct.get("productImageUrl")
        official_result["priceAmount"] = first_direct.get("priceAmount")
        official_result["priceCurrency"] = first_direct.get("priceCurrency")
        official_result["stockStatus"] = first_direct.get("stockStatus")
        official_result["isAvailable"] = first_direct.get("isAvailable")
        official_result["manufacturerInventoryId"] = first_direct.get("manufacturerInventoryId")
        official_result["regionCode"] = first_direct.get("regionCode")
        official_result["finSetup"] = first_direct.get("finSetup") or official_result.get("finSetup")

    exact_rows = execute_with_retry(
        exact_query,
        {
            "model_match": model_match,
            "model_family_match": model_family_match,
            "brand_id": official.BrandId,
            "board_model_id": official.BoardModelId,
            "length": official.LengthFeetInches,
            "length_title_match": length_title_match,
            "volume": official.VolumeLitres,
            "construction": official.Construction,
            "fin_setup": official.FinSetup,
            "brand_name": official.BrandName,
            "retailer_exact_construction_strict": retailer_exact_construction_strict,
            "region_code": region_code
        }
    )

    exact_matches = []
    brand_model_names = [official.ModelName]
    if any(row.BoardModelId is None for row in exact_rows):
        brand_model_names = [
            row.ModelName
            for row in execute_with_retry(
                text("""
                    SELECT ModelName
                    FROM dbo.BoardModels
                    WHERE BrandId = :brand_id
                      AND IsActive = 1
                """),
                {"brand_id": official.BrandId},
            )
        ]

    for row in exact_rows:
        strong_model_title = text_contains_phrase(
            row.RawProductTitle,
            row.NormalisedProductTitle,
            official.ModelName,
        )
        title_model_candidates = [
            model_name
            for model_name in brand_model_names
            if text_contains_phrase(
                row.RawProductTitle,
                row.NormalisedProductTitle,
                model_name,
            )
        ]
        deterministic_title_model = (
            row.BoardModelId is None
            and strong_model_title
            and len(title_model_candidates) == 1
            and clean_text(title_model_candidates[0]) == clean_text(official.ModelName)
        )
        exact, exact_reason = classify_retailer_exact(
            {
                "boardSizeId": row.BoardSizeId,
                "title": f"{row.RawProductTitle or ''} {row.NormalisedProductTitle or ''}",
                "length": row.LengthFeetInches,
                "width": row.Width,
                "thickness": row.Thickness,
                "volume": row.VolumeLitres,
                "construction": row.Construction,
            },
            {
                "boardSizeId": official.BoardSizeId,
                "length": official.LengthFeetInches,
                "width": official.Width,
                "thickness": official.Thickness,
                "volume": official.VolumeLitres,
                "construction": official.Construction,
            },
            brand_matches=row.BrandId == official.BrandId,
            model_matches=(
                row.BoardModelId == official.BoardModelId
                or deterministic_title_model
            ),
            strong_model_title=strong_model_title,
        )
        if not exact:
            continue

        result = retailer_result(row, "retailerExact")
        result["exactMatchReason"] = exact_reason
        exact_matches.append(result)

        if len(exact_matches) >= 50:
            break

    exact_ids = {
        row["inventoryId"]
        for row in exact_matches
    }

    close_rows = execute_with_retry(
        close_query,
        {
            "model_match": model_match,
            "model_family_match": model_family_match,
            "brand_id": official.BrandId,
            "length": official.LengthFeetInches,
            "one_down_length": one_down_length,
            "one_up_length": one_up_length,
            "length_title_match": length_title_match,
            "volume": official.VolumeLitres,
            "construction": official.Construction,
            "target_length_inches": target_length_inches or 0,
            "region_code": region_code
        }
    )

    close_matches = []

    for row in close_rows:
        if row.InventoryId in exact_ids:
            continue

        if not model_family_matches(
            row.RawProductTitle,
            row.NormalisedProductTitle,
            official.ModelName
        ):
            continue

        close_matches.append(
            retailer_result(
                row,
                "retailerClose"
            )
        )

        if len(close_matches) >= 50:
            break

    other_model_matches = []
    close_ids = {
        row["inventoryId"]
        for row in close_matches
    }

    if should_include_other_model_matches(
        official.BrandName,
        direct_matches,
        exact_matches,
        close_matches,
    ):
        other_model_matches_limit = configured_other_model_matches_limit()
        if should_run_other_model_matches(
            direct_matches,
            exact_matches,
            close_matches,
        ):
            excluded_inventory_ids = sorted(exact_ids | close_ids) or [-1]
            try:
                other_model_rows = execute_with_retry(
                    other_models_query,
                    {
                        "excluded_inventory_ids": excluded_inventory_ids,
                        "excluded_inventory_ids_empty": 1 if not (exact_ids or close_ids) else 0,
                        "board_size_id": official.BoardSizeId,
                        "board_model_id": official.BoardModelId,
                        "brand_id": official.BrandId,
                        "length": official.LengthFeetInches,
                        "one_down_length": one_down_length,
                        "one_up_length": one_up_length,
                        "two_down_length": two_down_length,
                        "two_up_length": two_up_length,
                        "volume": official.VolumeLitres,
                        "construction": official.Construction,
                        "region_code": region_code,
                    },
                    timeout_seconds=OTHER_MODEL_MATCHES_TIMEOUT_SECONDS,
                )

                for row in other_model_rows:
                    if should_exclude_close_retailer_row(
                        row,
                        official,
                        exact_ids | close_ids,
                    ):
                        continue

                    result = retailer_result(row, "retailerOtherModel")
                    result["canonicalModelName"] = getattr(row, "CanonicalModelName", None)
                    other_model_matches.append(result)

                    if len(other_model_matches) >= other_model_matches_limit:
                        break
            except Exception as exc:
                timeout_like = is_timeout_error(exc)
                search_log(
                    "other_model_matches_timeout" if timeout_like else "other_model_matches_skipped",
                    requestId=request_id,
                    boardSizeId=boardSizeId,
                    region=region_code,
                    brandName=official.BrandName,
                    modelName=official.ModelName,
                    construction=official.Construction,
                    length=official.LengthFeetInches,
                    elapsedMs=elapsed_ms(),
                    errorType=type(exc).__name__,
                    errorMessage=str(exc),
                )
                other_model_matches = []

    if official_result.get("directManufacturerMatches"):
        available_direct_matches = [
            match for match in official_result.get("directManufacturerMatches", [])
            if bool(match.get("isAvailable"))
        ]

        selected_direct_match = (
            available_direct_matches[0]
            if available_direct_matches
            else official_result["directManufacturerMatches"][0]
        )

        official_result["manufacturerAvailability"] = {
            "isAvailable": bool(selected_direct_match.get("isAvailable")),
            "stockStatus": selected_direct_match.get("stockStatus"),
            "productUrl": selected_direct_match.get("productUrl")
        }

        official_result["productUrl"] = (
            selected_direct_match.get("productUrl")
            or official_result.get("productUrl")
        )
        official_result["productImageUrl"] = selected_direct_match.get("productImageUrl")
        official_result["imageUrl"] = selected_direct_match.get("productImageUrl")
        official_result["priceAmount"] = selected_direct_match.get("priceAmount")
        official_result["priceCurrency"] = selected_direct_match.get("priceCurrency")
        official_result["stockStatus"] = selected_direct_match.get("stockStatus")
        official_result["isAvailable"] = selected_direct_match.get("isAvailable")
        official_result["manufacturerInventoryId"] = selected_direct_match.get("manufacturerInventoryId")
    else:
        official_result["manufacturerAvailability"] = {
            "isAvailable": False,
            "stockStatus": "unavailable",
            "productUrl": official_result.get("productUrl")
        }
        official_result["stockStatus"] = "unavailable"
        official_result["isAvailable"] = False

    response = {
        "apiBuild": "manufacturer-policy-v1-thin-fallback",
        "searchVersion": SEARCH_VERSION,
        "regionCode": region_code,
        "manufacturerSearchPolicy": {
            "brandName": official.BrandName,
            "manufacturerMode": manufacturer_mode,
            "directEnabled": bool(direct_enabled),
            "retailerExactConstructionStrict": bool(retailer_exact_construction_strict),
            "allowAlternateManufacturerConstruction": bool(allow_alternate_manufacturer_construction)
        },
        "manufacturer": official_result,
        "manufacturerAvailability": official_result.get("manufacturerAvailability"),
        "directManufacturerMatches": official_result.get("directManufacturerMatches", []),
        "alternateManufacturerMatches": official_result.get("alternateManufacturerMatches", []),
        "exactRetailerMatches": exact_matches,
        "closeRetailerMatches": close_matches,
        "otherModelMatches": other_model_matches,
    }

    search_log(
        "search_request_complete",
        requestId=request_id,
        boardSizeId=boardSizeId,
        region=region_code,
        brandName=official.BrandName,
        modelName=official.ModelName,
        construction=official.Construction,
        length=official.LengthFeetInches,
        totalDurationMs=elapsed_ms(),
        manufacturerDirectCount=len(response.get("directManufacturerMatches", [])),
        exactRetailerCount=len(response.get("exactRetailerMatches", [])),
        closeRetailerCount=len(response.get("closeRetailerMatches", [])),
        otherModelMatchesCount=len(response.get("otherModelMatches", [])),
    )
    return response


@app.get("/api/test-db")
def test_database_connection():

    result = fetch_one_with_retry(
        text("SELECT DB_NAME() AS database_name;")
    )

    return {
        "status": "connected",
        "database": result.database_name
    }
