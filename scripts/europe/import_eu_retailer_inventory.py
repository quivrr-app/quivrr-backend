from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


INPUT_FILE = Path(
    "scrapers/retailers/europe/shopify/output/eu_shopify_normalised_inventory.json"
)
BRANDS_FILE = Path("scrapers/brands/brands_seed.json")
BRAND_OUTPUT_ROOT = Path("scrapers/brands")
OUTPUT_FILE = Path("scripts/europe/output/eu_retailer_import_dry_run_report.json")

REGION_CODE = "EU"
PRICE_CURRENCY = "EUR"

BRAND_ALIASES = {
    "al merrick": "Channel Islands",
    "ci": "Channel Islands",
    "ci surfboards": "Channel Islands",
    "hayden shapes": "Haydenshapes",
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
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def rows_from_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        rows = payload.get("rows")

        if isinstance(rows, list):
            return rows

    return []


def load_input_rows(input_file: Path, retailer_slug: str) -> list[dict]:
    payload = load_json(input_file)
    rows = rows_from_payload(payload)

    if not retailer_slug:
        raise RuntimeError(
            "Dry-run importer requires --retailer for scaffold validation."
        )

    return [
        row
        for row in rows
        if clean(row.get("retailerSlug")) == retailer_slug
    ]


def load_brand_map() -> dict[str, str]:
    brand_map = {}

    if not BRANDS_FILE.exists():
        return brand_map

    brands = load_json(BRANDS_FILE)

    if not isinstance(brands, list):
        return brand_map

    for brand in brands:
        name = clean(
            brand.get("brand_name")
            or brand.get("brandName")
            or brand.get("name")
        )

        if name:
            brand_map[clean_key(name)] = name

    for alias, canonical in BRAND_ALIASES.items():
        brand_map[clean_key(alias)] = canonical

    return brand_map


def iter_catalogue_files() -> list[Path]:
    patterns = [
        "*/output/*master_catalogue_clean.json",
        "*/output/*master_catalogue.json",
        "*/output/*canonical*.json",
    ]
    files = []

    for pattern in patterns:
        files.extend(BRAND_OUTPUT_ROOT.glob(pattern))

    return sorted(set(files))


def extract_catalogue_rows(data: object) -> list[dict]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]

    if not isinstance(data, dict):
        return []

    for key in [
        "models",
        "boards",
        "products",
        "catalogue",
        "items",
        "rows",
    ]:
        value = data.get(key)

        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]

    return []


def first_model_name(row: dict) -> str:
    for key in [
        "modelName",
        "model_name",
        "model",
        "name",
        "title",
        "productTitle",
    ]:
        value = clean(row.get(key))

        if value:
            return value

    return ""


def first_brand_name(row: dict) -> str:
    for key in [
        "brandName",
        "brand_name",
        "brand",
        "vendor",
    ]:
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
            model = first_model_name(row)

            if not model:
                continue

            brand = first_brand_name(row)
            canonical_brand = brand_map.get(clean_key(brand), brand)
            brand_key = clean_key(canonical_brand)

            if not brand_key:
                continue

            model_map.setdefault(brand_key, set()).add(clean_key(model))

    return model_map


def mapped_brand_name(row: dict, brand_map: dict[str, str]) -> str:
    brand = clean(row.get("brandName"))

    return brand_map.get(clean_key(brand), "")


def model_maps(row: dict, brand_map: dict[str, str], model_map: dict[str, set[str]]) -> bool:
    brand = mapped_brand_name(row, brand_map)

    if not brand:
        return False

    model = clean(row.get("modelName"))

    if not model:
        return False

    known_models = model_map.get(clean_key(brand), set())

    return clean_key(model) in known_models


def matched_model_name(row: dict, brand_map: dict[str, str], model_map: dict[str, set[str]]) -> str:
    if not model_maps(row, brand_map, model_map):
        return ""

    return clean(row.get("modelName"))


def row_dedupe_key(row: dict) -> str:
    return "|".join([
        clean_key(row.get("retailerSlug")),
        clean_key(row.get("productUrl")),
        clean_key(row.get("brandName")),
        clean_key(row.get("modelName")),
        clean_key(row.get("lengthFeetInches")),
        clean(row.get("volumeLitres")),
        clean(row.get("priceAmount")),
    ])


def has_searchable_dimension(row: dict) -> bool:
    return bool(clean(row.get("lengthFeetInches")) or clean(row.get("volumeLitres")))


def has_stock_signal(row: dict) -> bool:
    return isinstance(row.get("isAvailable"), bool) or bool(clean(row.get("stockStatus")))


def has_missing_price(row: dict) -> bool:
    return not clean(row.get("priceAmount"))


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

    if not has_stock_signal(row):
        reasons.append("missing_stock_status")

    if not has_searchable_dimension(row):
        reasons.append("missing_all_dimensions")

    if has_missing_price(row):
        reasons.append("missing_price")

    return reasons


def canonical_review_reason(canonical_brand_matched: bool, canonical_model_matched: bool) -> str:
    reasons = []

    if not canonical_brand_matched:
        reasons.append("unknown_brand")

    if not canonical_model_matched:
        reasons.append("unknown_model")

    return ",".join(reasons)


def match_confidence(canonical_brand_matched: bool, canonical_model_matched: bool) -> str:
    if canonical_brand_matched and canonical_model_matched:
        return "canonical_brand_and_model"

    if canonical_brand_matched:
        return "canonical_brand_only"

    return "raw_only"



def build_report(rows: list[dict], retailer_slug: str) -> dict:
    brand_map = load_brand_map()
    model_map = load_model_map(brand_map)

    deduped = {}
    duplicate_count = 0
    true_reject_rows = []
    raw_importable_rows = []
    canonical_matched_rows = []
    canonical_review_rows = []
    reason_counts = Counter()
    true_reject_reason_counts = Counter()
    canonical_review_reason_counts = Counter()
    unknown_brands = Counter()
    unknown_models = Counter()

    for row in rows:
        key = row_dedupe_key(row)

        if key in deduped:
            duplicate_count += 1
            continue

        deduped[key] = row
        reject_reasons = true_reject_reasons(row)
        matched_brand = mapped_brand_name(row, brand_map)
        canonical_brand_matched = bool(matched_brand)
        canonical_model_matched = model_maps(row, brand_map, model_map)
        matched_model = matched_model_name(row, brand_map, model_map)
        review_reason = canonical_review_reason(
            canonical_brand_matched,
            canonical_model_matched,
        )
        needs_canonical_review = bool(review_reason)
        importable_raw = not reject_reasons

        for reason in reject_reasons:
            true_reject_reason_counts[reason] += 1
            reason_counts[reason] += 1

        if review_reason:
            for reason in review_reason.split(","):
                canonical_review_reason_counts[reason] += 1
                reason_counts[reason] += 1

        if not canonical_brand_matched:
            unknown_brands[clean(row.get("brandName")) or "missing"] += 1

        if not canonical_model_matched:
            model_key = " / ".join([
                clean(row.get("brandName")) or "missing_brand",
                clean(row.get("modelName")) or "missing_model",
            ])
            unknown_models[model_key] += 1

        dry_run_row = {
            "retailerSlug": clean(row.get("retailerSlug")),
            "retailerName": clean(row.get("retailerName")),
            "regionCode": clean(row.get("regionCode")),
            "brandName": clean(row.get("brandName")),
            "canonicalBrandMatched": canonical_brand_matched,
            "canonicalModelMatched": canonical_model_matched,
            "matchedBrandName": matched_brand or None,
            "matchedModelName": matched_model or None,
            "matchConfidence": match_confidence(
                canonical_brand_matched,
                canonical_model_matched,
            ),
            "modelName": clean(row.get("modelName")),
            "rawProductTitle": clean(row.get("rawProductTitle")),
            "productUrl": clean(row.get("productUrl")),
            "priceAmount": clean(row.get("priceAmount")),
            "priceCurrency": clean(row.get("priceCurrency")),
            "lengthFeetInches": clean(row.get("lengthFeetInches")),
            "volumeLitres": row.get("volumeLitres"),
            "isAvailable": row.get("isAvailable"),
            "stockStatus": clean(row.get("stockStatus")),
            "importableRaw": importable_raw,
            "needsCanonicalReview": needs_canonical_review,
            "reviewReason": review_reason or None,
            "trueRejectReasons": reject_reasons,
        }

        if importable_raw:
            raw_importable_rows.append(dry_run_row)

            if needs_canonical_review:
                canonical_review_rows.append(dry_run_row)
            else:
                canonical_matched_rows.append(dry_run_row)
        else:
            true_reject_rows.append(dry_run_row)

    rows_after_dedupe = list(deduped.values())
    missing_dimensions = [
        row for row in rows_after_dedupe if not has_searchable_dimension(row)
    ]
    missing_prices = [
        row for row in rows_after_dedupe if has_missing_price(row)
    ]

    if true_reject_rows:
        recommendation = "Needs major work"
    elif canonical_review_rows:
        recommendation = "Raw import ready, canonical review required"
    else:
        recommendation = "Ready for SQL importer"

    return {
        "mode": "dry_run",
        "purpose": "EU RetailerInventory raw importer simulation only. No SQL writes.",
        "inputFile": str(INPUT_FILE),
        "retailerSlug": retailer_slug,
        "regionCode": REGION_CODE,
        "priceCurrency": PRICE_CURRENCY,
        "sourceRows": len(rows),
        "rowsBeforeDedupe": len(rows),
        "rowsAfterDedupe": len(rows_after_dedupe),
        "duplicateRowsRemoved": duplicate_count,
        "metrics": {
            "rawImportableRows": len(raw_importable_rows),
            "canonicalMatchedRows": len(canonical_matched_rows),
            "needsCanonicalReview": len(canonical_review_rows),
            "trueRejects": len(true_reject_rows),
            "unknownBrands": sum(unknown_brands.values()),
            "unknownModels": sum(unknown_models.values()),
            "missingDimensions": len(missing_dimensions),
            "missingPrices": len(missing_prices),
        },
        "topReviewReasons": dict(reason_counts),
        "trueRejectReasonCounts": dict(true_reject_reason_counts),
        "canonicalReviewReasonCounts": dict(canonical_review_reason_counts),
        "unknownBrands": [
            {"brandName": brand, "count": count}
            for brand, count in unknown_brands.most_common()
        ],
        "unknownModels": [
            {"brandModel": model, "count": count}
            for model, count in unknown_models.most_common(50)
        ],
        "rawImportableSample": raw_importable_rows[:10],
        "canonicalMatchedSample": canonical_matched_rows[:10],
        "canonicalReviewSample": canonical_review_rows[:25],
        "trueRejectSample": true_reject_rows[:25],
        "recommendation": recommendation,
        "nextSqlImporterNotes": [
            "Create or update EU Retailers rows using RegionCode = EU.",
            "Insert RetailerInventory rows with PriceAmount and PriceCurrency, not PriceAud.",
            "Keep AU and ID importers separate from this EU path.",
            "Allow raw retailer inventory rows while keeping canonical review status explicit.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run EU retailer inventory import readiness without SQL writes."
    )
    parser.add_argument(
        "--retailer",
        required=True,
        help="Retailer slug to dry-run. Required to avoid accidental all-retailer runs.",
    )
    parser.add_argument(
        "--input",
        default=str(INPUT_FILE),
        help="Normalised EU inventory JSON input.",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_FILE),
        help="Dry-run report output path.",
    )
    args = parser.parse_args()

    input_file = Path(args.input)
    output_file = Path(args.output)

    rows = load_input_rows(input_file, args.retailer)
    report = build_report(rows, args.retailer)
    report["inputFile"] = str(input_file)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("EU retailer import dry-run complete")
    print(f"Retailer: {args.retailer}")
    print(f"Rows after dedupe: {report['rowsAfterDedupe']}")
    print(f"Raw importable rows: {report['metrics']['rawImportableRows']}")
    print(f"Needs canonical review: {report['metrics']['needsCanonicalReview']}")
    print(f"True rejects: {report['metrics']['trueRejects']}")
    print(f"Recommendation: {report['recommendation']}")
    print(f"Report: {output_file}")


if __name__ == "__main__":
    main()
