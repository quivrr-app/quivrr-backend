import json
import subprocess
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import engine

RETAILERS = [
    {
        "name": "BGS Bali",
        "website": "https://store.bgsbali.com",
        "script": "scrapers/retailers/indonesia/bgs_bali/build_bgs_bali_inventory.py",
        "output": "scrapers/retailers/indonesia/bgs_bali/output/bgs_bali_surfboards.json",
    },
    {
        "name": "White Monkey Surf",
        "website": "https://whitemonkeysurf.com",
        "script": "scrapers/retailers/indonesia/white_monkey/build_white_monkey_inventory.py",
        "output": "scrapers/retailers/indonesia/white_monkey/output/white_monkey_surfboards.json",
    },
    {
        "name": "Freefall Surf Industries",
        "website": "https://freefallsurfindustries.com",
        "script": "scrapers/retailers/indonesia/freefall/build_freefall_inventory.py",
        "output": "scrapers/retailers/indonesia/freefall/output/freefall_surfboards.json",
    },
    {
        "name": "Onboard Store Indonesia",
        "website": "https://www.onboardstore.id",
        "script": "scrapers/retailers/indonesia/onboard_store/build_onboard_store_inventory.py",
        "output": "scrapers/retailers/indonesia/onboard_store/output/onboard_store_surfboards.json",
    },
    {
        "name": "Boardriders Bali",
        "website": "https://boardridersbali.com",
        "script": "scrapers/retailers/indonesia/boardriders_bali/build_boardriders_bali_inventory.py",
        "output": "scrapers/retailers/indonesia/boardriders_bali/output/boardriders_bali_surfboards.json",
    },
    {
        "name": "Drifter Surf",
        "website": "https://driftersurf.com",
        "script": "scrapers/retailers/indonesia/drifter/build_drifter_inventory.py",
        "output": "scrapers/retailers/indonesia/drifter/output/drifter_surfboards.json",
    },
]

BRAND_ALIASES = {
    "Hayden Shapes": "Haydenshapes",
    "Lost": "Lost Surfboards",
    "Sharp Eye": "Sharp Eye",
    "Sharpeye": "Sharp Eye",
    "Native": None,
    "Drifter Surf": None,
    "Crowe Surfboards": None,
}


def clean(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def normalise(value):
    value = clean(value)
    return value.upper() if value else None


def decimal_or_none(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def run_sql(work, attempts=8):
    last = None

    for attempt in range(1, attempts + 1):
        try:
            with engine.begin() as conn:
                return work(conn)
        except OperationalError as exc:
            last = exc
            print(f"SQL failed attempt {attempt}, retrying...")
            time.sleep(min(attempt * 3, 15))

    raise last


def run_scrapers():
    for retailer in RETAILERS:
        script = Path(retailer["script"])

        if not script.exists():
            print(f"Missing scraper, skipping: {script}")
            continue

        print(f"Running {retailer['name']}...")
        subprocess.run([sys.executable, str(script)], check=True)


def load_rows():
    rows = []

    for retailer in RETAILERS:
        path = Path(retailer["output"])

        if not path.exists():
            print(f"Missing output, skipping: {path}")
            continue

        data = json.loads(path.read_text(encoding="utf-8"))

        for row in data:
            if row.get("isAvailable") is False:
                continue

            row["retailerName"] = retailer["name"]
            row["websiteUrl"] = retailer["website"]
            rows.append(row)

    return rows


def main():
    run_scrapers()

    rows = load_rows()
    print(f"Indonesia rows loaded: {len(rows)}")

    def import_work(conn):
        brand_rows = conn.execute(text("""
            SELECT BrandId, BrandName
            FROM dbo.Brands
            WHERE IsActive = 1
        """)).fetchall()

        brands = {r.BrandName.lower(): r.BrandId for r in brand_rows}

        retailer_ids = {}

        for retailer in RETAILERS:
            existing = conn.execute(text("""
                SELECT RetailerId
                FROM dbo.Retailers
                WHERE RetailerName = :name
            """), {"name": retailer["name"]}).fetchone()

            if existing:
                retailer_id = existing.RetailerId
                conn.execute(text("""
                    UPDATE dbo.Retailers
                    SET WebsiteUrl = :website,
                        Country = 'Indonesia',
                        RegionCode = 'ID',
                        IsActive = 1,
                        UpdatedAtUtc = SYSUTCDATETIME()
                    WHERE RetailerId = :retailer_id
                """), {
                    "retailer_id": retailer_id,
                    "website": retailer["website"],
                })
            else:
                retailer_id = conn.execute(text("""
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
                        :name,
                        :website,
                        'Indonesia',
                        'ID',
                        1,
                        SYSUTCDATETIME(),
                        SYSUTCDATETIME()
                    )
                """), {
                    "name": retailer["name"],
                    "website": retailer["website"],
                }).fetchone().RetailerId

            retailer_ids[retailer["name"]] = retailer_id

        conn.execute(text("""
            UPDATE dbo.RetailerInventory
            SET IsActive = 0,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE RegionCode = 'ID'
        """))

        insert_rows = []

        for row in rows:
            brand_name = clean(row.get("brandName"))
            mapped_brand = BRAND_ALIASES.get(brand_name, brand_name)
            brand_id = brands.get(mapped_brand.lower()) if mapped_brand else None

            currency = clean(row.get("currencyCode")) or clean(row.get("priceCurrency")) or "IDR"
            price_amount = decimal_or_none(row.get("priceAmount"))

            insert_rows.append({
                "retailer_id": retailer_ids[row["retailerName"]],
                "brand_id": brand_id,
                "raw_title": clean(row.get("rawProductTitle")) or clean(row.get("modelName")) or "Unknown surfboard",
                "normalised_title": normalise(row.get("rawProductTitle")) or normalise(row.get("modelName")),
                "product_url": clean(row.get("productUrl")),
                "product_image_url": clean(row.get("productImageUrl")),
                "price_aud": price_amount if currency == "AUD" else None,
                "price_amount": price_amount,
                "price_currency": currency,
                "stock_status": clean(row.get("stockStatus")) or "available",
                "construction": clean(row.get("construction")),
                "fin_setup": clean(row.get("finSetup")),
                "length": clean(row.get("lengthFeetInches")),
                "width": clean(row.get("width")),
                "thickness": clean(row.get("thickness")),
                "volume": decimal_or_none(row.get("volumeLitres")),
            })

        if insert_rows:
            conn.execute(text("""
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
                    :price_aud,
                    :price_amount,
                    :price_currency,
                    :stock_status,
                    NULL,
                    :construction,
                    :fin_setup,
                    :length,
                    :width,
                    :thickness,
                    :volume,
                    NULL,
                    10,
                    SYSUTCDATETIME(),
                    1,
                    SYSUTCDATETIME(),
                    SYSUTCDATETIME(),
                    'ID'
                )
            """), insert_rows)

        return len(insert_rows), retailer_ids

    inserted, retailer_ids = run_sql(import_work)

    print(f"Indonesia inventory inserted: {inserted}")
    print(retailer_ids)


if __name__ == "__main__":
    main()
