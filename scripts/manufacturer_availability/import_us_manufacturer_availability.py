from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.europe.import_eu_retailer_inventory import (  # noqa: E402
    build_engine,
    connect_with_retry,
    load_board_sizes,
    model_key,
    select_size_candidate,
)


REGION = "US"
SOURCE = "manufacturer_direct"
CHUNK_SIZE = 500
CONFIRM_TOKEN = "APPLY_US_MFA"
FILES = {
    "JS Industries": Path(
        "scrapers/manufacturers/availability/js_industries/output/js_industries_us_manufacturer_inventory.json"
    ),
    "Channel Islands": Path(
        "scrapers/manufacturers/availability/channel_islands/output/channel_islands_us_manufacturer_inventory.json"
    ),
    "Pyzel": Path(
        "scrapers/manufacturers/availability/pyzel/output/pyzel_us_manufacturer_inventory.json"
    ),
    "Firewire": Path(
        "scrapers/manufacturers/availability/firewire/output/firewire_us_manufacturer_inventory.json"
    ),
    "Album": Path(
        "scrapers/manufacturers/availability/album/output/album_us_manufacturer_inventory.json"
    ),
    "Haydenshapes": Path(
        "scrapers/manufacturers/availability/haydenshapes/output/haydenshapes_us_manufacturer_inventory.json"
    ),
    "DHD": Path(
        "scrapers/manufacturers/availability/dhd/output/dhd_us_manufacturer_inventory.json"
    ),
    "Rusty": Path(
        "scrapers/manufacturers/availability/rusty/output/rusty_us_manufacturer_inventory.json"
    ),
    "Sharp Eye": Path(
        "scrapers/manufacturers/availability/sharpeye/output/sharpeye_us_manufacturer_inventory.json"
    ),
    "Christenson": Path(
        "scrapers/manufacturers/availability/christenson/output/christenson_us_manufacturer_inventory.json"
    ),
    "Misfit Shapes": Path(
        "scrapers/manufacturers/availability/misfit/output/misfit_us_manufacturer_inventory.json"
    ),
    "Chilli": Path(
        "scrapers/manufacturers/availability/chilli/output/chilli_us_manufacturer_inventory.json"
    ),
    "Pukas": Path(
        "scrapers/manufacturers/availability/pukas/output/pukas_us_manufacturer_inventory.json"
    ),
}
REPORT_OUTPUT = Path("scripts/manufacturer_availability/output/us_mfa_import_report.json")
TEXT_COLUMN_LIMITS = {
    "BrandName": 200,
    "ModelName": 300,
    "RawProductTitle": 500,
    "ProductUrl": 1000,
    "ProductImageUrl": 1000,
    "LengthFeetInches": 50,
    "Width": 50,
    "Thickness": 50,
    "Construction": 100,
    "FinSetup": 100,
    "TailShape": 100,
    "PriceCurrency": 10,
    "StockStatus": 100,
    "Source": 200,
    "RegionCode": 20,
    "AvailabilitySource": 100,
    "SourceProductId": 200,
    "SourceVariantId": 200,
    "SourceVariantTitle": 300,
}
DECIMAL_QUANTUM = {
    "VolumeLitres": Decimal("0.01"),
    "PriceAmount": Decimal("0.01"),
}


def clean(value: object) -> str:
    return str(value or "").strip()


def load_rows(brands: set[str] | None = None) -> list[dict]:
    rows = []
    for brand, path in FILES.items():
        if brands and brand not in brands:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload:
            if row.get("regionCode") != REGION:
                raise RuntimeError(f"Unsafe row in {path}: RegionCode must be US")
            if row.get("availabilitySource") != SOURCE:
                raise RuntimeError(f"Unsafe row in {path}: availabilitySource must be manufacturer_direct")
            if row.get("priceAmount") is not None and not clean(row.get("priceCurrency")):
                raise RuntimeError(f"Unsafe row in {path}: priced rows must include priceCurrency")
            rows.append(row)
    return rows


def region_counts(conn) -> dict[str, int]:
    return {
        clean(row.RegionCode) or "<NULL>": int(row.InventoryRows)
        for row in conn.execute(
            text(
                """
                SELECT RegionCode, COUNT(*) AS InventoryRows
                FROM dbo.ManufacturerInventory
                GROUP BY RegionCode
                """
            )
        )
    }


def catalogue(conn):
    brands = {
        row.BrandName: int(row.BrandId)
        for row in conn.execute(text("SELECT BrandId, BrandName FROM dbo.Brands"))
    }
    models = defaultdict(lambda: defaultdict(list))
    for row in conn.execute(
        text(
            """
            SELECT BoardModelId, BrandId, ModelName
            FROM dbo.BoardModels
            """
        )
    ):
        models[int(row.BrandId)][model_key(row.ModelName)].append(int(row.BoardModelId))
    return brands, models, load_board_sizes(conn)


def prepare_rows(conn, rows: list[dict]) -> list[tuple[dict, int, int | None, int | None]]:
    brands, models, sizes = catalogue(conn)
    prepared = []
    for row in rows:
        brand_name = row["brandName"]
        brand_id = brands.get(brand_name)
        if brand_id is None:
            raise RuntimeError(f"Canonical brand missing: {brand_name}")
        matches = models[brand_id].get(model_key(row.get("modelName")), [])
        model_id = matches[0] if len(matches) == 1 else None
        size = (
            select_size_candidate(
                {
                    "lengthFeetInches": row.get("lengthFeetInches"),
                    "width": row.get("width"),
                    "thickness": row.get("thickness"),
                    "volumeLitres": row.get("volumeLitres"),
                    "construction": row.get("construction"),
                },
                model_id,
                sizes,
            )
            if model_id
            else None
        )
        prepared.append((row, brand_id, model_id, size["boardSizeId"] if size else None))
    return prepared


def diagnostics_from_prepared(prepared: list[tuple[dict, int, int | None, int | None]]) -> list[dict]:
    grouped: dict[str, list[tuple[dict, int, int | None, int | None]]] = defaultdict(list)
    for item in prepared:
        grouped[item[0]["brandName"]].append(item)
    diagnostics = []
    for brand, items in sorted(grouped.items()):
        diagnostics.append(
            {
                "brand": brand,
                "source_url": next((item[0].get("sourceUrl") or item[0].get("source_url") for item in items), None),
                "discovered_products": len({item[0].get("sourceProductId") for item in items}),
                "normalised_rows": len(items),
                "available_rows": sum(1 for item in items if item[0].get("isAvailable")),
                "linked_model_rows": sum(1 for item in items if item[2] is not None),
                "linked_size_rows": sum(1 for item in items if item[3] is not None),
            }
        )
    return diagnostics


def decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return None


def quantize_decimal(value: object, quantum: Decimal) -> float | None:
    number = decimal_or_none(value)
    if number is None:
        return None
    return float(number.quantize(quantum, rounding=ROUND_HALF_UP))


def trim_text(value: object, max_length: int) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    text = str(value).strip()
    if len(text) <= max_length:
        return text, False
    return text[:max_length].rstrip(), True


def conform_payload_for_schema(values: dict, columns: set[str]) -> tuple[dict, Counter]:
    conformed = dict(values)
    truncations: Counter = Counter()
    for field, quantum in DECIMAL_QUANTUM.items():
        if field in conformed:
            conformed[field] = quantize_decimal(conformed.get(field), quantum)
    for field, max_length in TEXT_COLUMN_LIMITS.items():
        if field not in conformed or field not in columns:
            continue
        conformed[field], trimmed = trim_text(conformed.get(field), max_length)
        if trimmed:
            truncations[field] += 1
    return conformed, truncations


def parse_utc_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    text = clean(value)
    if not text:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc).replace(
        tzinfo=None
    )


def make_payload(row: dict, brand_id: int, model_id: int | None, size_id: int | None, columns: set[str]) -> dict:
    checked_at = parse_utc_timestamp(row.get("lastCheckedUtc"))
    values = {
        "BrandId": brand_id,
        "BoardModelId": model_id,
        "BoardSizeId": size_id,
        "BrandName": row["brandName"],
        "ModelName": row.get("modelName"),
        "RawProductTitle": row.get("rawProductTitle"),
        "ProductUrl": row.get("productUrl"),
        "ProductImageUrl": row.get("productImageUrl"),
        "LengthFeetInches": row.get("lengthFeetInches"),
        "Width": row.get("width"),
        "Thickness": row.get("thickness"),
        "VolumeLitres": row.get("volumeLitres"),
        "Construction": row.get("construction"),
        "FinSetup": row.get("finSetup"),
        "TailShape": row.get("tailShape"),
        "PriceAmount": row.get("priceAmount"),
        "PriceCurrency": row.get("priceCurrency"),
        "StockStatus": row.get("stockStatus") or "available",
        "IsAvailable": 1 if row.get("isAvailable") else 0,
        "Source": SOURCE,
        "SourcePayload": json.dumps(row, ensure_ascii=False),
        "IsActive": 1,
        "RegionCode": REGION,
        "AvailabilitySource": SOURCE,
        "SourceProductId": row.get("sourceProductId"),
        "SourceVariantId": row.get("sourceVariantId"),
        "SourceVariantTitle": row.get("sourceVariantTitle"),
        "LastCheckedUtc": checked_at,
        "ScrapedAtUtc": checked_at,
        "CreatedAtUtc": checked_at,
        "UpdatedAtUtc": checked_at,
    }
    return {key: value for key, value in values.items() if key in columns}


def import_brand(engine, brand: str, rows: list[tuple[dict, int, int | None, int | None]]) -> dict:
    started = time.perf_counter()
    with connect_with_retry(engine) as conn:
        transaction = conn.begin()
        try:
            protected_before = region_counts(conn)
            columns = {
                row.COLUMN_NAME
                for row in conn.execute(
                    text(
                        """
                        SELECT COLUMN_NAME
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='ManufacturerInventory'
                        """
                    )
                )
            }
            brand_id = rows[0][1]
            deleted = conn.execute(
                text(
                    """
                    DELETE FROM dbo.ManufacturerInventory
                    WHERE BrandId = :brand_id
                      AND RegionCode = 'US'
                      AND AvailabilitySource = 'manufacturer_direct'
                    """
                ),
                {"brand_id": brand_id},
            ).rowcount

            truncations: Counter = Counter()
            payloads = []
            for item in rows:
                payload, item_truncations = conform_payload_for_schema(
                    make_payload(*item, columns),
                    columns,
                )
                payloads.append(payload)
                truncations.update(item_truncations)
            if not payloads:
                raise RuntimeError(f"No payloads to import for {brand}")
            names = list(payloads[0])
            statement = text(
                "INSERT INTO dbo.ManufacturerInventory ("
                + ",".join(f"[{name}]" for name in names)
                + ") VALUES ("
                + ",".join(f":{name}" for name in names)
                + ")"
            )
            inserted = 0
            for offset in range(0, len(payloads), CHUNK_SIZE):
                chunk = payloads[offset : offset + CHUNK_SIZE]
                conn.execute(statement, chunk)
                inserted += len(chunk)

            protected_after = region_counts(conn)
            if protected_after.get("AU") != protected_before.get("AU"):
                raise RuntimeError(f"AU ManufacturerInventory changed while importing {brand}")
            if protected_after.get("EU") != protected_before.get("EU"):
                raise RuntimeError(f"EU ManufacturerInventory changed while importing {brand}")
            if protected_after.get("ID") != protected_before.get("ID"):
                raise RuntimeError(f"ID ManufacturerInventory changed while importing {brand}")
            if protected_after.get("<NULL>", 0) != protected_before.get("<NULL>", 0):
                raise RuntimeError(f"NULL RegionCode rows changed while importing {brand}")
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise
    elapsed = time.perf_counter() - started
    return {
        "brand": brand,
        "rowsDeleted": max(deleted, 0),
        "rowsInserted": inserted,
        "elapsedSeconds": round(elapsed, 3),
        "truncatedFields": dict(truncations),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--brands", default="")
    parser.add_argument("--confirm-apply-us-mfa", default="")
    args = parser.parse_args()
    if args.apply and args.confirm_apply_us_mfa != CONFIRM_TOKEN:
        raise RuntimeError(
            f"US MFA apply mode requires explicit confirmation via --confirm-apply-us-mfa {CONFIRM_TOKEN}."
        )
    selected_brands = {item.strip() for item in args.brands.split(",") if item.strip()} or None
    rows = load_rows(selected_brands)
    engine = build_engine()
    with connect_with_retry(engine) as conn:
        before = region_counts(conn)
        prepared = prepare_rows(conn, rows)
    diagnostics = diagnostics_from_prepared(prepared)

    result = {
        "mode": "apply" if args.apply else "dry_run",
        "before": before,
        "brands": diagnostics,
    }
    if args.apply:
        grouped: dict[str, list[tuple[dict, int, int | None, int | None]]] = defaultdict(list)
        for item in prepared:
            grouped[item[0]["brandName"]].append(item)
        apply_diagnostics = []
        for brand in sorted(grouped):
            apply_diagnostics.append(import_brand(engine, brand, grouped[brand]))
        with connect_with_retry(engine) as conn:
            after = region_counts(conn)
        result["after"] = after
        result["applyDiagnostics"] = apply_diagnostics
    else:
        result["after"] = before

    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
