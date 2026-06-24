import os
import re
import time
from urllib.parse import quote_plus

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from utils.retailer_matching import classify_retailer_exact


load_dotenv()


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


def execute_with_retry(query, params=None, attempts=3):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                return list(
                    connection.execute(
                        query,
                        params or {}
                    )
                )

        except OperationalError as exc:
            last_error = exc

            if attempt == attempts:
                raise

            time.sleep(0.4 * attempt)

    raise last_error


def fetch_one_with_retry(query, params=None, attempts=3):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                return connection.execute(
                    query,
                    params or {}
                ).fetchone()

        except OperationalError as exc:
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


@app.get("/")
def root():

    return {
        "status": "online",
        "service": "quivrr-api"
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

    official = fetch_one_with_retry(
        official_query,
        {
            "board_size_id": boardSizeId
        }
    )

    if not official:
        return {
            "manufacturer": None,
            "exactRetailerMatches": [],
            "closeRetailerMatches": []
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

    return {
        "apiBuild": "manufacturer-policy-v1",
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
        "closeRetailerMatches": close_matches
    }


@app.get("/api/test-db")
def test_database_connection():

    result = fetch_one_with_retry(
        text("SELECT DB_NAME() AS database_name;")
    )

    return {
        "status": "connected",
        "database": result.database_name
    }
