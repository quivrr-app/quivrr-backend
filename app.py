import os
import re
import time
from urllib.parse import quote_plus

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


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

    parts = model.split()
    family_parts = []

    for part in parts:
        if re.search(r"\d", part):
            break

        family_parts.append(part)

    if family_parts:
        return " ".join(family_parts)

    return model


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

    if volume is None:
        volume_text = ""
    else:
        volume_text = f"{volume:g}L"

    return (
        f"{row.LengthFeetInches} x "
        f"{row.Width} x "
        f"{row.Thickness} / "
        f"{volume_text}"
    )


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


@app.get("/api/search")
def search_inventory(boardSizeId: int):

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
            mi.PriceAmount,
            mi.PriceCurrency,
            mi.StockStatus,
            mi.IsAvailable,
            mi.RegionCode,
            CASE
                WHEN mi.BoardSizeId = :board_size_id THEN 0
                WHEN mi.BoardModelId = :board_model_id
                  AND mi.LengthFeetInches = :length
                  AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                      REPLACE(REPLACE(:width, '"', ''), ' ', '')
                  AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                      REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                  THEN 1
                ELSE 9
            END AS MatchRank
        FROM dbo.ManufacturerInventory mi
        WHERE mi.IsActive = 1
          AND mi.RegionCode = 'AU'
          AND mi.AvailabilitySource = 'manufacturer_direct'
          AND mi.BrandId = :brand_id
          AND mi.BoardModelId = :board_model_id
          AND (
                mi.BoardSizeId = :board_size_id
             OR (
                    mi.BoardModelId = :board_model_id
                AND mi.LengthFeetInches = :length
                AND REPLACE(REPLACE(mi.Width, '"', ''), ' ', '') =
                    REPLACE(REPLACE(:width, '"', ''), ' ', '')
                AND REPLACE(REPLACE(mi.Thickness, '"', ''), ' ', '') =
                    REPLACE(REPLACE(:thickness, '"', ''), ' ', '')
                AND (
                       :volume IS NULL
                    OR mi.VolumeLitres IS NULL
                    OR ABS(CAST(mi.VolumeLitres AS float) - CAST(:volume AS float)) <= 0.75
                )
                AND (
                       :construction IS NULL
                    OR mi.Construction IS NULL
                    OR LOWER(mi.Construction) = LOWER(:construction)
                    OR LOWER(:construction) LIKE '%' + LOWER(mi.Construction) + '%'
                    OR LOWER(mi.Construction) LIKE '%' + LOWER(:construction) + '%'
                )
             )
          )
        ORDER BY
            CASE WHEN mi.IsAvailable = 1 THEN 0 ELSE 1 END,
            MatchRank ASC,
            CASE WHEN mi.BoardSizeId = :board_size_id THEN 0 ELSE 1 END,
            mi.PriceAmount ASC,
            mi.ManufacturerInventoryId ASC
    """)

    exact_query = text("""
        SELECT TOP 200
            ri.InventoryId,
            ri.RawProductTitle,
            ri.NormalisedProductTitle,
            ri.ProductUrl,
            ri.ProductImageUrl,
            ri.PriceAud,
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
        AND (
            ri.StockStatus IS NULL
            OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN (
                'in stock',
                'instock',
                'available',
                'true'
            )
        )
        AND (
            ri.LengthFeetInches = :length
            OR (
                ri.LengthFeetInches IS NULL
                AND (
                    ri.RawProductTitle LIKE :length_title_match
                    OR ri.NormalisedProductTitle LIKE :length_title_match
                )
            )
        )
        AND (
            ri.RawProductTitle LIKE :model_match
            OR ri.NormalisedProductTitle LIKE :model_match
            OR ri.RawProductTitle LIKE :model_family_match
            OR ri.NormalisedProductTitle LIKE :model_family_match
        )
        AND (
            ri.VolumeLitres IS NULL
            OR ABS(
                CAST(ri.VolumeLitres AS float)
                - CAST(:volume AS float)
            ) <= 0.75
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
                WHEN ri.RawProductTitle LIKE :model_family_match
                    OR ri.NormalisedProductTitle LIKE :model_family_match
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
        AND (
            ri.StockStatus IS NULL
            OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN (
                'in stock',
                'instock',
                'available',
                'true'
            )
        )
        AND (
            ri.RawProductTitle LIKE :model_match
            OR ri.NormalisedProductTitle LIKE :model_match
            OR ri.RawProductTitle LIKE :model_family_match
            OR ri.NormalisedProductTitle LIKE :model_family_match
        )
        AND (
            ri.LengthFeetInches = :length
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
            ri.VolumeLitres IS NULL
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
            "construction": official.Construction
        }
    )

    direct_matches = []

    for row in manufacturer_direct_rows:
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
            "priceAmount": float(row.PriceAmount) if row.PriceAmount is not None else None,
            "priceCurrency": row.PriceCurrency,
            "stockStatus": row.StockStatus,
            "isAvailable": bool(row.IsAvailable),
            "regionCode": row.RegionCode
        })

    if not direct_matches:
        fallback_direct = fetch_one_with_retry(
            text("""
                SELECT TOP 1
                    ManufacturerInventoryId,
                    BrandName,
                    ModelName,
                    ProductUrl,
                    ProductImageUrl,
                    LengthFeetInches,
                    Width,
                    Thickness,
                    VolumeLitres,
                    Construction,
                    PriceAmount,
                    PriceCurrency,
                    StockStatus,
                    IsAvailable,
                    RegionCode
                FROM dbo.ManufacturerInventory
                WHERE BoardSizeId = :board_size_id
                  AND IsActive = 1
                  AND RegionCode = 'AU'
                  AND AvailabilitySource = 'manufacturer_direct'
                ORDER BY
                    CASE WHEN IsAvailable = 1 THEN 0 ELSE 1 END,
                    ManufacturerInventoryId DESC
            """),
            {
                "board_size_id": official.BoardSizeId
            }
        )

        if fallback_direct:
            direct_matches.append({
                "resultType": "manufacturerDirect",
                "manufacturerInventoryId": fallback_direct.ManufacturerInventoryId,
                "brandName": fallback_direct.BrandName,
                "modelName": fallback_direct.ModelName,
                "productUrl": fallback_direct.ProductUrl,
                "productImageUrl": fallback_direct.ProductImageUrl,
                "imageUrl": fallback_direct.ProductImageUrl,
                "length": fallback_direct.LengthFeetInches,
                "width": fallback_direct.Width,
                "thickness": fallback_direct.Thickness,
                "volumeLitres": format_volume(fallback_direct.VolumeLitres),
                "construction": fallback_direct.Construction,
                "priceAmount": float(fallback_direct.PriceAmount) if fallback_direct.PriceAmount is not None else None,
                "priceCurrency": fallback_direct.PriceCurrency,
                "stockStatus": fallback_direct.StockStatus,
                "isAvailable": bool(fallback_direct.IsAvailable),
                "regionCode": fallback_direct.RegionCode
            })

    official_result["directManufacturerMatches"] = direct_matches
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

    direct_stock = fetch_one_with_retry(
        text("""
            SELECT TOP 1
                ManufacturerInventoryId,
                ProductUrl,
                ProductImageUrl,
                StockStatus,
                IsAvailable,
                PriceAmount,
                PriceCurrency
            FROM dbo.ManufacturerInventory
            WHERE IsActive = 1
              AND RegionCode = 'AU'
              AND AvailabilitySource = 'manufacturer_direct'
              AND BoardSizeId = :board_size_id
            ORDER BY
                CASE WHEN IsAvailable = 1 THEN 0 ELSE 1 END,
                ManufacturerInventoryId DESC
        """),
        {
            "board_size_id": official.BoardSizeId
        }
    )

    official_result["manufacturerAvailability"] = {
        "isAvailable": bool(direct_stock and direct_stock.IsAvailable),
        "stockStatus": direct_stock.StockStatus if direct_stock else "sold_out",
        "productUrl": direct_stock.ProductUrl if direct_stock else None
    }

    if direct_stock:
        official_result["manufacturerInventoryId"] = direct_stock.ManufacturerInventoryId
        official_result["isAvailable"] = bool(direct_stock.IsAvailable)
        official_result["stockStatus"] = direct_stock.StockStatus
        official_result["productUrl"] = direct_stock.ProductUrl or official_result.get("productUrl")
        official_result["productImageUrl"] = direct_stock.ProductImageUrl
        official_result["imageUrl"] = direct_stock.ProductImageUrl
        official_result["priceAmount"] = float(direct_stock.PriceAmount) if direct_stock.PriceAmount is not None else None
        official_result["priceCurrency"] = direct_stock.PriceCurrency

    exact_rows = execute_with_retry(
        exact_query,
        {
            "model_match": model_match,
            "model_family_match": model_family_match,
            "length": official.LengthFeetInches,
            "length_title_match": length_title_match,
            "volume": official.VolumeLitres,
            "construction": official.Construction,
            "fin_setup": official.FinSetup
        }
    )

    exact_matches = []

    for row in exact_rows:
        if not model_name_matches(
            row.RawProductTitle,
            row.NormalisedProductTitle,
            official.ModelName
        ):
            continue

        exact_matches.append(
            retailer_result(
                row,
                "retailerExact"
            )
        )

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
            "length": official.LengthFeetInches,
            "one_down_length": one_down_length,
            "one_up_length": one_up_length,
            "length_title_match": length_title_match,
            "volume": official.VolumeLitres,
            "construction": official.Construction,
            "target_length_inches": target_length_inches or 0
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

    return {
        "manufacturer": official_result,
        "manufacturerAvailability": official_result.get("manufacturerAvailability"),
        "directManufacturerMatches": official_result.get("directManufacturerMatches", []),
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