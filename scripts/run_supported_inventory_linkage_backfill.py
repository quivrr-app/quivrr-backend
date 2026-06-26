from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.europe import import_eu_retailer_inventory as eu_import


SUPPORTED_BRANDS = (
    "Album",
    "Channel Islands",
    "Chemistry Surfboards",
    "Chilli",
    "Christenson",
    "DHD",
    "DMS",
    "Firewire",
    "Haydenshapes",
    "JS Industries",
    "Lost",
    "Misfit",
    "Pukas",
    "Pyzel",
    "Rusty",
    "Sharp Eye",
    "Simon Anderson",
)
SUPPORTED_BRAND_SET = set(SUPPORTED_BRANDS)
OUTPUT_FILE = Path("scripts/output/supported_inventory_linkage_backfill_report.json")
CONFIRM_TOKEN = "APPLY_SUPPORTED_LINKS"


def row_dimensions(row: dict) -> dict[str, object]:
    title_dimensions = eu_import.dimensions_from_title(row.get("rawProductTitle"))
    return {
        "lengthFeetInches": row.get("lengthFeetInches") or title_dimensions.get("length"),
        "width": row.get("width") or title_dimensions.get("width"),
        "thickness": row.get("thickness") or title_dimensions.get("thickness"),
        "volumeLitres": row.get("volumeLitres") or title_dimensions.get("volume"),
    }


def has_size_family_candidate(
    row: dict,
    board_model_id: int,
    sizes_by_model: dict[int, list[dict]],
) -> bool:
    source_dimensions = row_dimensions(row)
    length = eu_import.clean(source_dimensions["lengthFeetInches"])
    length_inches = eu_import.length_to_inches(length)
    if length_inches is None:
        return False

    candidates = [
        dict(size)
        for size in sizes_by_model.get(board_model_id, [])
        if eu_import.length_to_inches(size.get("lengthFeetInches")) == length_inches
    ]
    if not candidates:
        return False

    for field, tolerance_value in (
        ("width", eu_import.DEFAULT_WIDTH_TOLERANCE),
        ("thickness", eu_import.DEFAULT_THICKNESS_TOLERANCE),
    ):
        if eu_import.measurement_key(source_dimensions.get(field)) is None:
            continue
        equivalent = [
            item
            for item in candidates
            if eu_import.measurements_within(
                source_dimensions.get(field),
                item.get(field),
                tolerance_value,
            )
        ]
        if not equivalent:
            return False
        candidates = equivalent

    title_constructions = eu_import.construction_from_title(row.get("rawProductTitle"))
    source_construction = (
        next(iter(title_constructions))
        if len(title_constructions) == 1
        else eu_import.construction_key(row.get("construction"))
    )
    if source_construction:
        matching_construction = [
            item
            for item in candidates
            if eu_import.construction_key(item.get("construction")) == source_construction
        ]
        if not matching_construction:
            return False
        candidates = matching_construction

    return bool(candidates)


def load_active_inventory_rows(conn) -> list[dict]:
    rows = conn.execute(
        eu_import.text(
            """
            SELECT
                ri.InventoryId,
                r.RetailerName,
                ri.RegionCode,
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
                ri.Construction
            FROM dbo.RetailerInventory ri
            INNER JOIN dbo.Retailers r
                ON r.RetailerId = ri.RetailerId
            LEFT JOIN dbo.Brands b
                ON b.BrandId = ri.BrandId
            WHERE ri.IsActive = 1
            """
        )
    ).fetchall()

    inventory = []
    for row in rows:
        inventory.append(
            {
                "inventoryId": int(eu_import.row_field(row, "InventoryId")),
                "retailerName": eu_import.clean(eu_import.row_field(row, "RetailerName")),
                "regionCode": eu_import.clean(eu_import.row_field(row, "RegionCode")),
                "brandId": int(eu_import.row_field(row, "BrandId"))
                if eu_import.row_field(row, "BrandId") is not None
                else None,
                "brandName": eu_import.clean(eu_import.row_field(row, "BrandName")),
                "boardModelId": int(eu_import.row_field(row, "BoardModelId"))
                if eu_import.row_field(row, "BoardModelId") is not None
                else None,
                "boardSizeId": int(eu_import.row_field(row, "BoardSizeId"))
                if eu_import.row_field(row, "BoardSizeId") is not None
                else None,
                "rawProductTitle": eu_import.clean(
                    eu_import.row_field(row, "RawProductTitle")
                ),
                "normalisedProductTitle": eu_import.clean(
                    eu_import.row_field(row, "NormalisedProductTitle")
                ),
                "lengthFeetInches": eu_import.clean(
                    eu_import.row_field(row, "LengthFeetInches")
                ),
                "width": eu_import.clean(eu_import.row_field(row, "Width")),
                "thickness": eu_import.clean(eu_import.row_field(row, "Thickness")),
                "volumeLitres": eu_import.decimal_or_none(
                    eu_import.row_field(row, "VolumeLitres")
                ),
                "construction": eu_import.clean(
                    eu_import.row_field(row, "Construction")
                ),
            }
        )
    return inventory


def compute_supported_linkage_report(conn) -> dict:
    brands = eu_import.brand_lookup(conn)
    models_by_brand = eu_import.load_board_models(conn)
    sizes_by_model = eu_import.load_board_sizes(conn)
    inventory_rows = load_active_inventory_rows(conn)
    supported_model_ids = {
        model["boardModelId"]
        for brand_models in models_by_brand.values()
        for model in brand_models
    }

    brand_updates = []
    model_updates = []
    size_updates = []
    alias_opportunities = Counter()
    unmatched_models = Counter()
    unmatched_examples: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    retailer_metrics: dict[tuple[str, str], Counter] = defaultdict(Counter)
    manufacturer_metrics: dict[tuple[str, str], Counter] = defaultdict(Counter)
    retailer_model_coverage: dict[str, set[int]] = defaultdict(set)
    global_metrics = Counter()

    for row in inventory_rows:
        parsed_brand = eu_import.extract_canonical_brand_name(
            row.get("rawProductTitle"),
            row.get("brandName"),
        )
        effective_brand_name = parsed_brand or row.get("brandName")
        if effective_brand_name not in SUPPORTED_BRAND_SET:
            continue

        region_code = row["regionCode"] or "UNKNOWN"
        retailer_key = (region_code, row["retailerName"] or "missing")
        manufacturer_key = (region_code, effective_brand_name)
        retailer_metrics[retailer_key]["supportedRowsBefore"] += 1
        manufacturer_metrics[manufacturer_key]["supportedRowsBefore"] += 1
        global_metrics["supportedRowsBefore"] += 1

        effective_brand_id = row.get("brandId")
        if effective_brand_id is None and parsed_brand:
            effective_brand_id = brands.get(eu_import.clean_key(parsed_brand))
            if effective_brand_id is not None:
                brand_updates.append(
                    {
                        "inventory_id": row["inventoryId"],
                        "region_code": region_code,
                        "brand_id": effective_brand_id,
                    }
                )

        if row.get("boardModelId") is not None:
            effective_model_id = row["boardModelId"]
            retailer_metrics[retailer_key]["linkedModelRowsBefore"] += 1
            manufacturer_metrics[manufacturer_key]["linkedModelRowsBefore"] += 1
            global_metrics["linkedModelRowsBefore"] += 1
        else:
            effective_model_id = None

        if row.get("boardSizeId") is not None:
            retailer_metrics[retailer_key]["linkedSizeRowsBefore"] += 1
            manufacturer_metrics[manufacturer_key]["linkedSizeRowsBefore"] += 1
            global_metrics["linkedSizeRowsBefore"] += 1

        parsed_model = eu_import.extract_model_hint(
            row.get("rawProductTitle"),
            effective_brand_name,
        )
        match_row = {
            **row,
            "brandId": effective_brand_id,
            "brandName": effective_brand_name,
            "parsedModel": parsed_model,
        }

        selected_model = None
        if effective_model_id is None and effective_brand_id is not None:
            selected_model = eu_import.select_model_candidate(match_row, models_by_brand)
            if selected_model and not selected_model.get("ambiguous"):
                effective_model_id = selected_model["boardModelId"]
                model_updates.append(
                    {
                        "inventory_id": row["inventoryId"],
                        "region_code": region_code,
                        "board_model_id": effective_model_id,
                        "normalised_title": selected_model["modelName"],
                    }
                )

        projected_model_linked = effective_model_id is not None
        projected_size_linked = row.get("boardSizeId") is not None

        if not projected_size_linked and effective_model_id is not None:
            selected_size = eu_import.select_size_candidate(
                match_row,
                effective_model_id,
                sizes_by_model,
            )
            if selected_size:
                projected_size_linked = True
                size_updates.append(
                    {
                        "inventory_id": row["inventoryId"],
                        "region_code": region_code,
                        "board_size_id": selected_size["boardSizeId"],
                    }
                )

        if projected_model_linked:
            retailer_metrics[retailer_key]["linkedModelRowsAfter"] += 1
            manufacturer_metrics[manufacturer_key]["linkedModelRowsAfter"] += 1
            global_metrics["linkedModelRowsAfter"] += 1
            retailer_model_coverage[region_code].add(int(effective_model_id))
        else:
            unmatched_key = (
                region_code,
                effective_brand_name,
                parsed_model or "<missing>",
            )
            unmatched_models[unmatched_key] += 1
            alias_opportunities[(effective_brand_name, parsed_model or "<missing>")] += 1
            if len(unmatched_examples[unmatched_key]) < 3:
                unmatched_examples[unmatched_key].append(row["rawProductTitle"])

        projected_size_family_linked = False
        if effective_model_id is not None:
            projected_size_family_linked = has_size_family_candidate(
                match_row,
                int(effective_model_id),
                sizes_by_model,
            )
        if projected_size_family_linked:
            retailer_metrics[retailer_key]["linkedSizeFamilyRowsAfter"] += 1
            manufacturer_metrics[manufacturer_key]["linkedSizeFamilyRowsAfter"] += 1
            global_metrics["linkedSizeFamilyRowsAfter"] += 1

        if projected_size_linked:
            retailer_metrics[retailer_key]["linkedSizeRowsAfter"] += 1
            manufacturer_metrics[manufacturer_key]["linkedSizeRowsAfter"] += 1
            global_metrics["linkedSizeRowsAfter"] += 1

    global_metrics["supportedRowsAfter"] = global_metrics["supportedRowsBefore"]

    def pct(numerator: int, denominator: int) -> float:
        if not denominator:
            return 0.0
        return round((numerator / denominator) * 100, 2)

    def build_breakdown(source: dict[tuple[str, str], Counter]) -> list[dict]:
        rows = []
        for (region_code, label), metrics in sorted(source.items()):
            total = int(metrics["supportedRowsBefore"])
            rows.append(
                {
                    "regionCode": region_code,
                    "name": label,
                    "supportedRows": total,
                    "linkedModelRowsBefore": int(metrics["linkedModelRowsBefore"]),
                    "linkedModelRowsAfter": int(metrics["linkedModelRowsAfter"]),
                    "linkedSizeFamilyRowsAfter": int(metrics["linkedSizeFamilyRowsAfter"]),
                    "linkedSizeRowsBefore": int(metrics["linkedSizeRowsBefore"]),
                    "linkedSizeRowsAfter": int(metrics["linkedSizeRowsAfter"]),
                    "linkedModelPctBefore": pct(int(metrics["linkedModelRowsBefore"]), total),
                    "linkedModelPctAfter": pct(int(metrics["linkedModelRowsAfter"]), total),
                    "linkedSizeFamilyPctAfter": pct(int(metrics["linkedSizeFamilyRowsAfter"]), total),
                    "linkedSizePctBefore": pct(int(metrics["linkedSizeRowsBefore"]), total),
                    "linkedSizePctAfter": pct(int(metrics["linkedSizeRowsAfter"]), total),
                }
            )
        return rows

    region_breakdown = []
    region_totals: dict[str, Counter] = defaultdict(Counter)
    for item in build_breakdown(retailer_metrics):
        region_code = item["regionCode"]
        region_totals[region_code]["supportedRows"] += item["supportedRows"]
        region_totals[region_code]["linkedModelRowsBefore"] += item["linkedModelRowsBefore"]
        region_totals[region_code]["linkedModelRowsAfter"] += item["linkedModelRowsAfter"]
        region_totals[region_code]["linkedSizeFamilyRowsAfter"] += item["linkedSizeFamilyRowsAfter"]
        region_totals[region_code]["linkedSizeRowsBefore"] += item["linkedSizeRowsBefore"]
        region_totals[region_code]["linkedSizeRowsAfter"] += item["linkedSizeRowsAfter"]
    for region_code, metrics in sorted(region_totals.items()):
        total = int(metrics["supportedRows"])
        region_breakdown.append(
            {
                "regionCode": region_code,
                "supportedRows": total,
                "linkedModelRowsBefore": int(metrics["linkedModelRowsBefore"]),
                "linkedModelRowsAfter": int(metrics["linkedModelRowsAfter"]),
                "linkedSizeFamilyRowsAfter": int(metrics["linkedSizeFamilyRowsAfter"]),
                "linkedSizeRowsBefore": int(metrics["linkedSizeRowsBefore"]),
                "linkedSizeRowsAfter": int(metrics["linkedSizeRowsAfter"]),
                "linkedModelPctBefore": pct(int(metrics["linkedModelRowsBefore"]), total),
                "linkedModelPctAfter": pct(int(metrics["linkedModelRowsAfter"]), total),
                "linkedSizeFamilyPctAfter": pct(int(metrics["linkedSizeFamilyRowsAfter"]), total),
                "linkedSizePctBefore": pct(int(metrics["linkedSizeRowsBefore"]), total),
                "linkedSizePctAfter": pct(int(metrics["linkedSizeRowsAfter"]), total),
                "projectedRetailerModelCount": len(retailer_model_coverage.get(region_code, set())),
            }
        )

    return {
        "supportedBrands": list(SUPPORTED_BRANDS),
        "global": {
            "supportedRows": int(global_metrics["supportedRowsBefore"]),
            "linkedModelRowsBefore": int(global_metrics["linkedModelRowsBefore"]),
            "linkedModelRowsAfter": int(global_metrics["linkedModelRowsAfter"]),
            "linkedSizeFamilyRowsAfter": int(global_metrics["linkedSizeFamilyRowsAfter"]),
            "linkedSizeRowsBefore": int(global_metrics["linkedSizeRowsBefore"]),
            "linkedSizeRowsAfter": int(global_metrics["linkedSizeRowsAfter"]),
            "linkedModelPctBefore": pct(
                int(global_metrics["linkedModelRowsBefore"]),
                int(global_metrics["supportedRowsBefore"]),
            ),
            "linkedModelPctAfter": pct(
                int(global_metrics["linkedModelRowsAfter"]),
                int(global_metrics["supportedRowsBefore"]),
            ),
            "linkedSizeFamilyPctAfter": pct(
                int(global_metrics["linkedSizeFamilyRowsAfter"]),
                int(global_metrics["supportedRowsBefore"]),
            ),
            "linkedSizePctBefore": pct(
                int(global_metrics["linkedSizeRowsBefore"]),
                int(global_metrics["supportedRowsBefore"]),
            ),
            "linkedSizePctAfter": pct(
                int(global_metrics["linkedSizeRowsAfter"]),
                int(global_metrics["supportedRowsBefore"]),
            ),
            "unlinkedModelRowsBefore": int(global_metrics["supportedRowsBefore"] - global_metrics["linkedModelRowsBefore"]),
            "unlinkedModelRowsAfter": int(global_metrics["supportedRowsBefore"] - global_metrics["linkedModelRowsAfter"]),
            "unlinkedSizeRowsBefore": int(global_metrics["supportedRowsBefore"] - global_metrics["linkedSizeRowsBefore"]),
            "unlinkedSizeRowsAfter": int(global_metrics["supportedRowsBefore"] - global_metrics["linkedSizeRowsAfter"]),
        },
        "regionBreakdown": region_breakdown,
            "retailerBreakdown": build_breakdown(retailer_metrics),
        "manufacturerBreakdown": build_breakdown(manufacturer_metrics),
        "regionCoverage": [
            {
                "regionCode": region_code,
                "supportedModelCount": len(supported_model_ids),
                "projectedRetailerModelCount": len(model_ids),
                "projectedRetailerModelIds": sorted(model_ids),
            }
            for region_code, model_ids in sorted(retailer_model_coverage.items())
        ],
        "topRemainingUnmatchedModels": [
            {
                "regionCode": region_code,
                "brandName": brand_name,
                "parsedModel": model_name,
                "count": count,
                "examples": unmatched_examples[(region_code, brand_name, model_name)],
            }
            for (region_code, brand_name, model_name), count in unmatched_models.most_common(40)
        ],
        "topAliasOpportunities": [
            {
                "brandName": brand_name,
                "parsedModel": parsed_model,
                "count": count,
            }
            for (brand_name, parsed_model), count in alias_opportunities.most_common(40)
            if parsed_model not in {"", "<missing>"}
        ],
        "updates": {
            "brandUpdates": brand_updates,
            "modelUpdates": model_updates,
            "sizeUpdates": size_updates,
        },
    }


def apply_updates(conn, updates: dict) -> dict:
    brand_updates = updates["brandUpdates"]
    model_updates = updates["modelUpdates"]
    size_updates = updates["sizeUpdates"]

    if brand_updates:
        conn.execute(
            eu_import.text(
                """
                UPDATE dbo.RetailerInventory
                SET BrandId = :brand_id,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE InventoryId = :inventory_id
                  AND RegionCode = :region_code
                  AND BrandId IS NULL
                """
            ),
            brand_updates,
        )

    if model_updates:
        conn.execute(
            eu_import.text(
                """
                UPDATE dbo.RetailerInventory
                SET BoardModelId = :board_model_id,
                    NormalisedProductTitle = :normalised_title,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE InventoryId = :inventory_id
                  AND RegionCode = :region_code
                  AND BoardModelId IS NULL
                """
            ),
            model_updates,
        )

    if size_updates:
        conn.execute(
            eu_import.text(
                """
                UPDATE dbo.RetailerInventory
                SET BoardSizeId = :board_size_id,
                    UpdatedAtUtc = SYSUTCDATETIME()
                WHERE InventoryId = :inventory_id
                  AND RegionCode = :region_code
                  AND BoardSizeId IS NULL
                """
            ),
            size_updates,
        )

    return {
        "brandUpdatesApplied": len(brand_updates),
        "modelUpdatesApplied": len(model_updates),
        "sizeUpdatesApplied": len(size_updates),
    }


def write_report(report: dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


def print_summary(report: dict) -> None:
    global_metrics = report["global"]
    print(
        "Supported inventory linkage:",
        f"models {global_metrics['linkedModelPctBefore']}% -> {global_metrics['linkedModelPctAfter']}%",
        f"sizes {global_metrics['linkedSizePctBefore']}% -> {global_metrics['linkedSizePctAfter']}%",
    )
    for region in report["regionBreakdown"]:
        print(
            f"{region['regionCode']}:",
            f"supported={region['supportedRows']}",
            f"models {region['linkedModelPctBefore']}% -> {region['linkedModelPctAfter']}%",
            f"sizes {region['linkedSizePctBefore']}% -> {region['linkedSizePctAfter']}%",
        )
    print(f"Report: {OUTPUT_FILE}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or apply supported-manufacturer retailer linkage backfill.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("dry-run", "apply"),
        default="dry-run",
    )
    parser.add_argument("--confirm-apply", dest="confirm_apply")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = eu_import.build_engine()

    if args.mode == "apply" and args.confirm_apply != CONFIRM_TOKEN:
        raise SystemExit(
            f"Refusing apply mode without --confirm-apply {CONFIRM_TOKEN}"
        )

    with eu_import.connect_with_retry(engine) as conn:
        report = compute_supported_linkage_report(conn)

    if args.mode == "apply":
        with eu_import.begin_with_retry(engine) as conn:
            apply_result = apply_updates(conn, report["updates"])
        with eu_import.connect_with_retry(engine) as conn:
            after_report = compute_supported_linkage_report(conn)
        after_report["applyResult"] = apply_result
        write_report(after_report)
        print_summary(after_report)
        return

    write_report(report)
    print_summary(report)


if __name__ == "__main__":
    main()
