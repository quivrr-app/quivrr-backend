from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.europe import import_eu_retailer_inventory as eu_import  # noqa: E402
from scripts.usa.us_link_projection_rules import (  # noqa: E402
    excluded_product_type,
    normalise_brand_and_model_for_projection,
)


REGION_CODE = "US"
PRICE_CURRENCY = "USD"
DEFAULT_INPUT = Path("scrapers/retailers/usa/output/us_normalised_inventory.json")
DEFAULT_OUTPUT = Path("scripts/usa/output/us_inventory_quality_report.json")


def clean(value: object) -> str:
    return eu_import.clean(value)


def load_rows(input_path: Path) -> list[dict]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("rows", [])
    if not isinstance(rows, list):
        raise RuntimeError(f"USA quality report input has no rows list: {input_path}")
    return [row for row in rows if isinstance(row, dict)]


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
    if not eu_import.has_stock_signal(row):
        reasons.append("missing_stock_status")
    if not eu_import.has_searchable_dimension(row):
        reasons.append("missing_all_dimensions")
    return reasons


def _catalogue_sizes_for_row(row: dict) -> list[dict]:
    sizes = row.get("sizes")
    if isinstance(sizes, list) and sizes:
        extracted = []
        for size in sizes:
            if not isinstance(size, dict):
                continue
            extracted.append(
                {
                    "lengthFeetInches": clean(
                        size.get("lengthFeetInches")
                        or size.get("length_feet_inches")
                        or size.get("length")
                    ),
                    "width": clean(size.get("width")),
                    "thickness": clean(size.get("thickness")),
                    "volumeLitres": eu_import.decimal_or_none(
                        size.get("volumeLitres")
                        or size.get("volume_litres")
                        or size.get("volume")
                    ),
                    "construction": clean(
                        size.get("construction") or row.get("construction")
                    ),
                }
            )
        return extracted

    return [
        {
            "lengthFeetInches": clean(
                row.get("lengthFeetInches")
                or row.get("length_feet_inches")
                or row.get("length")
            ),
            "width": clean(row.get("width")),
            "thickness": clean(row.get("thickness")),
            "volumeLitres": eu_import.decimal_or_none(
                row.get("volumeLitres")
                or row.get("volume_litres")
                or row.get("volume")
            ),
            "construction": clean(row.get("construction")),
        }
    ]


def build_local_catalogue() -> tuple[dict[str, int], dict[int, list[dict]], dict[int, list[dict]], dict[int, str]]:
    brand_map = eu_import.load_brand_map()
    brand_ids: dict[str, int] = {}
    models_by_brand: dict[int, list[dict]] = defaultdict(list)
    sizes_by_model: dict[int, list[dict]] = defaultdict(list)
    model_id_to_name: dict[int, str] = {}
    seen_model_ids: dict[tuple[str, str], int] = {}
    seen_sizes: set[tuple[int, str, str, str, str, str]] = set()
    next_brand_id = 1
    next_model_id = 1
    next_size_id = 1

    for path in eu_import.iter_catalogue_files():
        try:
            rows = eu_import.extract_catalogue_rows(eu_import.load_json(path))
        except Exception:
            continue

        for row in rows:
            brand_name = eu_import.first_value(
                row, ["brandName", "brand_name", "brand", "vendor"]
            )
            model_name = eu_import.first_value(
                row,
                ["modelName", "model_name", "model", "name", "title", "productTitle"],
            )
            canonical_brand = brand_map.get(eu_import.clean_key(brand_name), brand_name)
            model_key = eu_import.catalogue_model_key(model_name, canonical_brand)
            if not canonical_brand or not model_name or not model_key:
                continue

            brand_key = eu_import.clean_key(canonical_brand)
            if brand_key not in brand_ids:
                brand_ids[brand_key] = next_brand_id
                next_brand_id += 1
            brand_id = brand_ids[brand_key]

            model_identity = (brand_key, model_key)
            if model_identity not in seen_model_ids:
                seen_model_ids[model_identity] = next_model_id
                models_by_brand[brand_id].append(
                    {
                        "boardModelId": next_model_id,
                        "brandId": brand_id,
                        "modelName": model_name,
                        "modelKey": model_key,
                    }
                )
                model_id_to_name[next_model_id] = model_name
                next_model_id += 1
            board_model_id = seen_model_ids[model_identity]

            for size in _catalogue_sizes_for_row(row):
                size_key = (
                    board_model_id,
                    clean(size.get("lengthFeetInches")),
                    clean(size.get("width")),
                    clean(size.get("thickness")),
                    clean(size.get("volumeLitres")),
                    clean(size.get("construction")),
                )
                if size_key in seen_sizes:
                    continue
                seen_sizes.add(size_key)
                sizes_by_model[board_model_id].append(
                    {
                        "boardSizeId": next_size_id,
                        "boardModelId": board_model_id,
                        "lengthFeetInches": size.get("lengthFeetInches"),
                        "width": size.get("width"),
                        "thickness": size.get("thickness"),
                        "volumeLitres": size.get("volumeLitres"),
                        "construction": size.get("construction"),
                    }
                )
                next_size_id += 1

    return brand_ids, dict(models_by_brand), dict(sizes_by_model), model_id_to_name


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def build_quality_report(rows: list[dict], input_path: Path) -> dict:
    brand_ids, models_by_brand, sizes_by_model, model_id_to_name = build_local_catalogue()

    deduped: dict[str, dict] = {}
    duplicate_rows = 0
    rejected_rows = 0
    reject_reason_counts = Counter()
    brand_distribution = Counter()
    retailer_distribution = Counter()
    missing_dimensions = 0
    missing_prices = 0
    missing_images = 0
    expected_model_links = 0
    expected_size_links = 0
    post_exclusion_rows = 0
    eligible_rows = 0
    eligible_model_links = 0
    eligible_size_links = 0
    expected_link_by_retailer: dict[str, Counter] = defaultdict(Counter)
    zero_link_reason_by_retailer: dict[str, Counter] = defaultdict(Counter)
    parsing_fix_counts = Counter()

    for row in rows:
        key = eu_import.row_dedupe_key(row)
        if key in deduped:
            duplicate_rows += 1
            continue
        deduped[key] = row

    for row in deduped.values():
        retailer_slug = clean(row.get("retailerSlug")) or "<missing>"
        retailer_name = clean(row.get("retailerName")) or retailer_slug
        raw_brand = clean(row.get("brandName"))
        extracted_brand = eu_import.extract_canonical_brand_name(
            row.get("rawProductTitle"), raw_brand
        )
        brand_name = extracted_brand or raw_brand or "Unknown"

        retailer_distribution[retailer_name] += 1
        brand_distribution[brand_name] += 1

        if not eu_import.has_searchable_dimension(row):
            missing_dimensions += 1
        if not clean(row.get("priceAmount")):
            missing_prices += 1
        if not clean(row.get("productImageUrl")):
            missing_images += 1

        reject_reasons = true_reject_reasons(row)
        if reject_reasons:
            rejected_rows += 1
            reject_reason_counts.update(reject_reasons)
            continue

        projection_brand, projection_model, parsing_reasons = (
            normalise_brand_and_model_for_projection(row)
        )
        for reason in parsing_reasons:
            parsing_fix_counts[reason] += 1

        expected_link_by_retailer[retailer_name]["importableRows"] += 1

        exclusion_reason = excluded_product_type(
            {
                **row,
                "brandName": projection_brand or brand_name,
                "modelName": projection_model or row.get("modelName"),
            }
        )
        if exclusion_reason:
            expected_link_by_retailer[retailer_name]["excludedRows"] += 1
            zero_link_reason_by_retailer[retailer_name][exclusion_reason] += 1
            continue

        post_exclusion_rows += 1
        expected_link_by_retailer[retailer_name]["postExclusionRows"] += 1

        canonical_brand_id = brand_ids.get(
            eu_import.clean_key(projection_brand or brand_name)
        )
        if canonical_brand_id is None:
            expected_link_by_retailer[retailer_name]["unlinkedModels"] += 1
            zero_link_reason_by_retailer[retailer_name]["missing_canonical_brand"] += 1
            continue

        eligible_rows += 1
        expected_link_by_retailer[retailer_name]["eligibleRows"] += 1

        match_row = {
            "brandId": canonical_brand_id,
            "brandName": projection_brand or brand_name,
            "rawProductTitle": clean(row.get("rawProductTitle")),
            "normalisedProductTitle": clean(projection_model)
            or clean(row.get("modelName"))
            or clean(row.get("rawProductTitle")),
            "parsedModel": clean(projection_model) or clean(row.get("modelName")),
            "lengthFeetInches": clean(row.get("lengthFeetInches")),
            "width": clean(row.get("width")),
            "thickness": clean(row.get("thickness")),
            "volumeLitres": row.get("volumeLitres"),
            "construction": clean(row.get("construction")),
        }
        model_candidate = eu_import.select_model_candidate(match_row, models_by_brand)
        if not model_candidate:
            expected_link_by_retailer[retailer_name]["unlinkedModels"] += 1
            zero_link_reason_by_retailer[retailer_name]["missing_canonical_model"] += 1
            continue

        expected_model_links += 1
        eligible_model_links += 1
        expected_link_by_retailer[retailer_name]["linkedModels"] += 1
        match_row["boardModelId"] = model_candidate["boardModelId"]
        match_row["matchedModelName"] = model_id_to_name.get(model_candidate["boardModelId"])

        size_candidate = eu_import.select_size_candidate(
            match_row, model_candidate["boardModelId"], sizes_by_model
        )
        if size_candidate:
            expected_size_links += 1
            eligible_size_links += 1
            expected_link_by_retailer[retailer_name]["linkedSizes"] += 1
        else:
            expected_link_by_retailer[retailer_name]["unlinkedSizes"] += 1
            zero_link_reason_by_retailer[retailer_name]["missing_canonical_sizes"] += 1

    total_rows = len(deduped)
    importable_rows = total_rows - rejected_rows
    before_model_pct = pct(expected_model_links, importable_rows)
    before_size_pct = pct(expected_size_links, importable_rows)
    after_model_pct = pct(eligible_model_links, eligible_rows)
    after_size_pct = pct(eligible_size_links, eligible_rows)

    return {
        "event": "us_inventory_quality_report",
        "regionCode": REGION_CODE,
        "priceCurrency": PRICE_CURRENCY,
        "inputFile": str(input_path),
        "sourceRows": len(rows),
        "totalRows": total_rows,
        "duplicateRows": duplicate_rows,
        "duplicateRatePct": pct(duplicate_rows, len(rows)),
        "importableRows": importable_rows,
        "rejectedRows": rejected_rows,
        "rejectedRatePct": pct(rejected_rows, total_rows),
        "productsWithoutDimensions": missing_dimensions,
        "productsWithoutDimensionsPct": pct(missing_dimensions, total_rows),
        "productsWithoutPrices": missing_prices,
        "productsWithoutPricesPct": pct(missing_prices, total_rows),
        "productsWithoutImages": missing_images,
        "productsWithoutImagesPct": pct(missing_images, total_rows),
        "projectedLinkMetricsBefore": {
            "denominator": "all_importable_rows",
            "importableRows": importable_rows,
            "projectedModelLinkedRows": expected_model_links,
            "projectedModelLinkedPct": before_model_pct,
            "projectedSizeLinkedRows": expected_size_links,
            "projectedSizeLinkedPct": before_size_pct,
        },
        "projectedLinkMetricsAfter": {
            "denominator": "catalogue_covered_eligible_rows_after_safe_us_normalisation_and_exclusions",
            "postExclusionRows": post_exclusion_rows,
            "eligibleRows": eligible_rows,
            "projectedModelLinkedRows": eligible_model_links,
            "projectedModelLinkedPct": after_model_pct,
            "projectedSizeLinkedRows": eligible_size_links,
            "projectedSizeLinkedPct": after_size_pct,
        },
        "expectedCanonicalModelLinkedRows": expected_model_links,
        "expectedCanonicalModelLinkedPct": before_model_pct,
        "expectedBoardSizeLinkedRows": expected_size_links,
        "expectedBoardSizeLinkedPct": before_size_pct,
        "brandDistribution": [
            {"brandName": brand, "rows": count}
            for brand, count in brand_distribution.most_common()
        ],
        "retailerDistribution": [
            {"retailerName": retailer, "rows": count}
            for retailer, count in retailer_distribution.most_common()
        ],
        "rejectReasonCounts": dict(reject_reason_counts),
        "parsingFixCounts": dict(parsing_fix_counts),
        "expectedLinkByRetailer": [
            {
                "retailerName": retailer,
                "importableRows": counts["importableRows"],
                "postExclusionRows": counts["postExclusionRows"],
                "eligibleRows": counts["eligibleRows"],
                "excludedRows": counts["excludedRows"],
                "expectedCanonicalModelLinkedRows": counts["linkedModels"],
                "expectedCanonicalModelLinkedPct": pct(
                    counts["linkedModels"], counts["importableRows"]
                ),
                "expectedCanonicalModelLinkedPctOnEligibleRows": pct(
                    counts["linkedModels"], counts["eligibleRows"]
                ),
                "expectedBoardSizeLinkedRows": counts["linkedSizes"],
                "expectedBoardSizeLinkedPct": pct(
                    counts["linkedSizes"], counts["importableRows"]
                ),
                "expectedBoardSizeLinkedPctOnEligibleRows": pct(
                    counts["linkedSizes"], counts["eligibleRows"]
                ),
                "zeroLinkReasons": dict(zero_link_reason_by_retailer.get(retailer, {})),
            }
            for retailer, counts in sorted(expected_link_by_retailer.items())
        ],
        "recommendation": (
            "Ready for guarded SQL apply review"
            if importable_rows > 0 and pct(rejected_rows, total_rows) <= 5.0
            else "Not ready for SQL apply"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a USA retailer inventory quality report from local dry-run output."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows = load_rows(args.input)
    report = build_quality_report(rows, args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("USA inventory quality report complete")
    print(f"Total rows: {report['totalRows']}")
    print(f"Importable rows: {report['importableRows']}")
    print(f"Rejected rows: {report['rejectedRows']}")
    print(
        "Projected canonical links on all importable rows:"
        f" models={report['projectedLinkMetricsBefore']['projectedModelLinkedRows']}"
        f" ({report['projectedLinkMetricsBefore']['projectedModelLinkedPct']}%)"
        f", sizes={report['projectedLinkMetricsBefore']['projectedSizeLinkedRows']}"
        f" ({report['projectedLinkMetricsBefore']['projectedSizeLinkedPct']}%)"
    )
    print(
        "Projected canonical links on eligible rows:"
        f" models={report['projectedLinkMetricsAfter']['projectedModelLinkedRows']}"
        f" ({report['projectedLinkMetricsAfter']['projectedModelLinkedPct']}%)"
        f", sizes={report['projectedLinkMetricsAfter']['projectedSizeLinkedRows']}"
        f" ({report['projectedLinkMetricsAfter']['projectedSizeLinkedPct']}%)"
    )
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
