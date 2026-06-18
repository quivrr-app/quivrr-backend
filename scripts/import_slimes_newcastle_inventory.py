import os
import re
import time
from decimal import Decimal
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


RETAILER_NAME = "Slimes Newcastle"
REGION_CODE = "AU"
BASE_URL = "https://www.slimesnewcastle.com.au"
COLLECTION = "surfboards"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
}

BRAND_ALIASES = {
    "JS Industries": ["JS ", "BARON", "MONSTA", "XERO", "BIG BARON", "BLACK BARON", "BULL RUN"],
    "Channel Islands": ["CI ", "CHANNEL ISLANDS", "BLACK BEAUTY", "BETTER EVERYDAY", "3DX", "3DV", "C.I. ", "HAPPY EVERYDAY"],
    "DHD": ["DHD ", "PHOENIX", "DX1", "BLACK DIAMOND"],
    "Lost": ["LOST ", "MAYHEM", "DRIVER", "PUDDLE JUMPER", "RAD RIPPER", "SUB DRIVER"],
    "Pyzel": ["PYZEL", "GHOST", "PHANTOM", "PYZALIEN"],
    "Firewire": ["FIREWIRE", "SLATER DESIGNS", "TOMO", "MACHADO", "SEASIDE", "DOMINATOR", "FRK", "MASHUP", "SWEET POTATO"],
    "Rusty": ["RUSTY"],
    "Haydenshapes": ["HAYDENSHAPES", "HAYDEN SHAPES", "HYPTO"],
    "Sharp Eye": ["SHARPEYE", "SHARP EYE", "INFERNO"],
    "Chilli": ["CHILLI"],
}

SKIP_TERMS = [
    "wetsuit",
    "leash",
    "tail pad",
    "traction",
    "deck grip",
    "wax",
    "tee",
    "shirt",
    "hoodie",
    "jumper",
    "sunglasses",
    "bottle",
    "glove",
    "resin kit",
    "uv resin",
    "seacured",
]


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch_products():
    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/collections/{COLLECTION}/products.json?limit=250&page={page}"
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        response.raise_for_status()

        batch = response.json().get("products", [])

        if not batch:
            break

        products.extend(batch)

        if len(batch) < 250:
            break

        page += 1
        time.sleep(0.3)

    return products


def is_surfboard(product):
    title = clean(product.get("title")).lower()
    product_type = clean(product.get("product_type")).lower()
    tags = " ".join(product.get("tags") or []).lower()
    combined = f"{title} {product_type} {tags}"

    return not any(term in combined for term in SKIP_TERMS)


def detect_brand(title):
    upper = f" {title.upper()} "

    for brand_name, aliases in BRAND_ALIASES.items():
        for alias in aliases:
            if alias.upper() in upper:
                return brand_name

    return None


def detect_construction(title):
    upper = title.upper()

    construction_patterns = [
        ("HYFI 3.0", "HYFI 3.0"),
        ("CARBOTUNE", "CarboTune"),
        ("SPINE-TEK", "Spine-Tek"),
        ("SPINETEK", "Spine-Tek"),
        ("IBOLIC", "I-Bolic"),
        ("I-BOLIC", "I-Bolic"),
        ("VOLCANIC", "Volcanic"),
        ("HELIUM", "Helium"),
        ("THUNDERBOLT CARBON", "Thunderbolt Carbon"),
        ("THUNDERBOLT RED", "Thunderbolt Red"),
        ("THUNDERBOLT", "Thunderbolt"),
        ("BLACK SHEEP", "Black Sheep"),
        ("LIGHTSPEED", "LightSpeed"),
        ("FUTUREFLEX", "FutureFlex"),
        ("TMRW TECH", "TMRW Tech"),
        ("ECT EPS", "ECT EPS"),
        ("EPS", "EPS"),
        ("PU", "PU"),
        ("PE", "PE"),
    ]

    for marker, value in construction_patterns:
        if marker in upper:
            return value

    return None


def detect_fin_setup(title):
    upper = title.upper()

    if "FCSII" in upper or "FCS II" in upper or "FCS 2" in upper:
        return "FCS II"

    if "FUTURES" in upper:
        return "Futures"

    if "GLASSED ON" in upper:
        return "Glassed On"

    if "SINGLE" in upper:
        return "Single"

    if "TWIN" in upper:
        return "Twin"

    return None


def parse_dimensions(title):
    text_value = clean(title)
    text_value = text_value.replace("×", "x")
    text_value = text_value.replace(" X ", " x ")

    match = re.search(
        r"""
        (?P<length>\d+'\s*\d{1,2})
        \s*x\s*
        (?P<width>\d+(?:\s+\d+/\d+)?)
        \s*x\s*
        (?P<thickness>\d+(?:\s+\d+/\d+)?)
        \s*[-x]\s*
        (?P<volume>\d+(?:\.\d+)?)\s*L
        """,
        text_value,
        re.IGNORECASE | re.VERBOSE,
    )

    if not match:
        return {
            "length": None,
            "width": None,
            "thickness": None,
            "volume_litres": None,
        }

    return {
        "length": clean(match.group("length").replace(" ", "")),
        "width": clean(match.group("width")),
        "thickness": clean(match.group("thickness")),
        "volume_litres": Decimal(match.group("volume")),
    }


def parse_decimal(value):
    if value in [None, ""]:
        return None

    try:
        return Decimal(str(value).replace(",", "").strip())
    except Exception:
        return None


def first_image(product):
    images = product.get("images") or []

    if images:
        return images[0].get("src")

    image = product.get("image")

    if isinstance(image, dict):
        return image.get("src")

    return None


def variant_title(product, variant):
    title = clean(product.get("title"))
    variant_name = clean(variant.get("title"))

    if variant_name and variant_name.lower() != "default title":
        return f"{title} {variant_name}"

    return title


def build_engine():
    load_dotenv()

    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")

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

    return create_engine(
        "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_string),
        pool_pre_ping=True,
    )


def main():
    print("")
    print("=" * 100)
    print("SLIMES NEWCASTLE DEDICATED INVENTORY IMPORT")
    print("=" * 100)

    products = fetch_products()
    surfboards = [product for product in products if is_surfboard(product)]

    print("")
    print("Products fetched:", len(products))
    print("Surfboard candidates:", len(surfboards))

    engine = build_engine()

    with engine.begin() as conn:
        retailer = conn.execute(text("""
            SELECT RetailerId
            FROM dbo.Retailers
            WHERE RetailerName = :retailer_name
              AND RegionCode = :region_code;
        """), {
            "retailer_name": RETAILER_NAME,
            "region_code": REGION_CODE,
        }).fetchone()

        if not retailer:
            raise RuntimeError("Slimes Newcastle retailer record not found in SQL")

        retailer_id = retailer.RetailerId

        brand_rows = conn.execute(text("""
            SELECT BrandId, BrandName
            FROM dbo.Brands;
        """)).fetchall()

        brand_lookup = {
            row.BrandName.lower(): row.BrandId
            for row in brand_rows
        }

        conn.execute(text("""
            DELETE FROM dbo.RetailerInventory
            WHERE RetailerId = :retailer_id
              AND RegionCode = :region_code;
        """), {
            "retailer_id": retailer_id,
            "region_code": REGION_CODE,
        })

        inserted = 0
        skipped_unavailable = 0
        skipped_duplicates = 0
        parsed_dimensions = 0
        seen = set()

        total_products = len(surfboards)

        for index, product in enumerate(surfboards, start=1):
            product_title = clean(product.get("title"))
            print(f"[{index}/{total_products}] {product_title}")

            detected_brand = detect_brand(product_title)
            brand_id = brand_lookup.get(detected_brand.lower()) if detected_brand else None

            product_url = f"{BASE_URL}/products/{product.get('handle')}"
            image_url = first_image(product)

            for variant in product.get("variants") or []:
                available = bool(variant.get("available"))

                if not available:
                    skipped_unavailable += 1
                    continue

                title = variant_title(product, variant)
                price = parse_decimal(variant.get("price"))

                dimensions = parse_dimensions(title)

                if dimensions["length"] and dimensions["volume_litres"] is not None:
                    parsed_dimensions += 1

                construction = detect_construction(title)
                fin_setup = detect_fin_setup(title)

                dedupe_key = (
                    product_url.lower(),
                    title.upper(),
                    str(price),
                )

                if dedupe_key in seen:
                    skipped_duplicates += 1
                    continue

                seen.add(dedupe_key)

                conn.execute(text("""
                    INSERT INTO dbo.RetailerInventory (
                        RetailerId,
                        RegionCode,
                        BrandId,
                        BoardModelId,
                        BoardSizeId,
                        RawProductTitle,
                        NormalisedProductTitle,
                        ProductUrl,
                        ProductImageUrl,
                        PriceAud,
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
                        UpdatedAtUtc
                    )
                    VALUES (
                        :retailer_id,
                        :region_code,
                        :brand_id,
                        NULL,
                        NULL,
                        :raw_title,
                        :normalised_title,
                        :product_url,
                        :product_image_url,
                        :price_aud,
                        'available',
                        NULL,
                        :construction,
                        :fin_setup,
                        :length,
                        :width,
                        :thickness,
                        :volume_litres,
                        NULL,
                        :confidence,
                        SYSUTCDATETIME(),
                        1,
                        SYSUTCDATETIME(),
                        SYSUTCDATETIME()
                    );
                """), {
                    "retailer_id": retailer_id,
                    "region_code": REGION_CODE,
                    "brand_id": brand_id,
                    "raw_title": title,
                    "normalised_title": title.upper(),
                    "product_url": product_url,
                    "product_image_url": image_url,
                    "price_aud": price,
                    "construction": construction,
                    "fin_setup": fin_setup,
                    "length": dimensions["length"],
                    "width": dimensions["width"],
                    "thickness": dimensions["thickness"],
                    "volume_litres": dimensions["volume_litres"],
                    "confidence": Decimal("20.0") if brand_id and dimensions["length"] else Decimal("10.0"),
                })

                inserted += 1

        conn.execute(text("""
            UPDATE dbo.Retailers
            SET
                IsActive = 1,
                UpdatedAtUtc = SYSUTCDATETIME(),
                LastVerifiedUtc = SYSUTCDATETIME()
            WHERE RetailerId = :retailer_id;
        """), {"retailer_id": retailer_id})

        verify = conn.execute(text("""
            SELECT
                r.RetailerName,
                COUNT(ri.InventoryId) AS InventoryRows,
                SUM(CASE WHEN ri.IsActive = 1 THEN 1 ELSE 0 END) AS ActiveRows,
                COUNT(DISTINCT ri.BrandId) AS MatchedBrands,
                SUM(CASE WHEN ri.LengthFeetInches IS NOT NULL THEN 1 ELSE 0 END) AS RowsWithLength,
                SUM(CASE WHEN ri.VolumeLitres IS NOT NULL THEN 1 ELSE 0 END) AS RowsWithVolume,
                MAX(ri.LastCheckedUtc) AS LastCheckedUtc
            FROM dbo.Retailers r
            LEFT JOIN dbo.RetailerInventory ri
                ON r.RetailerId = ri.RetailerId
            WHERE r.RetailerId = :retailer_id
            GROUP BY r.RetailerName;
        """), {"retailer_id": retailer_id}).fetchone()

        print("")
        print("Rows inserted:", inserted)
        print("Parsed dimensions:", parsed_dimensions)
        print("Skipped unavailable:", skipped_unavailable)
        print("Skipped duplicates:", skipped_duplicates)
        print(dict(verify._mapping))


if __name__ == "__main__":
    main()
