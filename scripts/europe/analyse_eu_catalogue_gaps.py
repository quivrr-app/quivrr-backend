from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.europe.import_eu_retailer_inventory import (
    BRAND_ALIASES,
    brand_lookup,
    build_canonical_link_report,
    clean,
    clean_key,
    connect_with_retry,
    decimal_or_none,
    extract_canonical_brand_name,
    extract_model_hint,
    load_board_models,
    load_board_sizes,
    model_key,
    tolerant_model_key,
    build_engine,
)


OUTPUT_JSON = Path("scripts/europe/output/eu_catalogue_gap_analysis.json")
OUTPUT_MODELS_CSV = Path("scripts/europe/output/eu_top_250_missing_models.csv")
OUTPUT_ALL_MODELS_CSV = Path("scripts/europe/output/eu_all_missing_models_ranked.csv")
OUTPUT_SIZES_CSV = Path("scripts/europe/output/eu_top_250_missing_sizes.csv")


def row_value(row, name: str):
    return row._mapping.get(name)


def load_incomplete_rows(conn) -> list[dict]:
    rows = conn.execute(text("""
        SELECT
            ri.InventoryId,
            r.RetailerName,
            ri.BrandId,
            b.BrandName,
            ri.BoardModelId,
            bm.ModelName AS LinkedModelName,
            ri.BoardSizeId,
            ri.RawProductTitle,
            ri.NormalisedProductTitle,
            ri.LengthFeetInches,
            ri.VolumeLitres
        FROM dbo.RetailerInventory ri
        INNER JOIN dbo.Retailers r
          ON r.RetailerId = ri.RetailerId
         AND r.RegionCode = 'EU'
        LEFT JOIN dbo.Brands b ON b.BrandId = ri.BrandId
        LEFT JOIN dbo.BoardModels bm ON bm.BoardModelId = ri.BoardModelId
        WHERE ri.RegionCode = 'EU'
          AND (ri.BoardModelId IS NULL OR ri.BoardSizeId IS NULL)
    """)).fetchall()
    return [{name: row_value(row, name) for name in row._mapping} for row in rows]


def raw_brand_candidate(title: object) -> str:
    value = clean(title)
    patterns = [
        r"^(.+?)\s+surfboards?\s+-",
        r"^(.+?)\s+surfboards?\s+\d",
        r"^(.+?)\s+surfboards?\b",
        r"^(.+?)\s+-\s+",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            return clean(match.group(1))
    return ""


def parser_failure_reason(model: str, title: str) -> str:
    if not model:
        return "model_parse_empty"
    key = model_key(model)
    if re.search(r"\b[4-9]\s*['’]\s*\d", model):
        return "length_left_in_model"
    if "surfboard" in key:
        return "brand_or_product_type_left_in_model"
    if re.search(r"\b(?:white|black|blue|red|orange|pink|sand|grey|gray|coral|mustard|burgundy|cream|taupe|olive|mint|colour|color)\b", key):
        return "colour_left_in_model"
    if re.search(
        r"\b(?:pu|eps|pe|tet|lct|futures|fcs|hyfi|helium|ibolic|volcanic|"
        r"carbon wrap|spine tek|ecoskin|polish|\d+f)\b",
        key,
    ):
        return "construction_or_fin_left_in_model"
    if len(key.split()) > 8 or any(token in model for token in ("+", "|")):
        return "merchandising_title_not_reduced"
    if re.search(r"\bby\s+[a-z]", key):
        return "shaper_suffix_left_in_model"
    if not re.search(r"[a-z]", key):
        return "model_parse_empty"
    return ""


def closest_model_status(parsed_model: str, catalogue_models: list[dict]) -> tuple[str, str]:
    parsed_key = model_key(parsed_model)
    tolerant_key = tolerant_model_key(parsed_model)
    compact_key = re.sub(r"[^a-z0-9]+", "", parsed_key)
    for model in catalogue_models:
        if parsed_key == model["modelKey"]:
            return "exact_catalogue_model_not_linked", model["modelName"]
        if tolerant_key and tolerant_key == tolerant_model_key(model["modelName"]):
            return "model_alias_or_suffix_failure", model["modelName"]
        canonical_compact_key = re.sub(r"[^a-z0-9]+", "", model["modelKey"])
        if compact_key and compact_key == canonical_compact_key:
            return "model_alias_or_suffix_failure", model["modelName"]
    return "", ""


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def remediation_classification(category: str) -> str:
    if category in {"exact_catalogue_model_not_linked", "model_alias_or_suffix_failure", "alias_failure"}:
        return "Existing model alias"
    if category == "genuine_new_model_absent_from_catalogue":
        return "Genuine missing model"
    if category == "unknown_brand_or_alias_failure":
        return "Brand not yet supported"
    return "Parsing failure"


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only EU canonical catalogue gap analysis.")
    parser.add_argument("--output", default=str(OUTPUT_JSON))
    args = parser.parse_args()

    engine = build_engine()
    with connect_with_retry(engine) as conn:
        rows = load_incomplete_rows(conn)
        brands = brand_lookup(conn)
        models_by_brand = load_board_models(conn)
        sizes_by_model = load_board_sizes(conn)
        linker_dry_run = build_canonical_link_report(conn)

    brand_names_by_id = {brand_id: name for name, brand_id in brands.items()}
    model_groups: dict[tuple, dict] = {}
    size_groups: dict[tuple, dict] = {}
    remediation = Counter()
    category_counts = Counter()
    size_category_counts = Counter()

    for row in rows:
        title = clean(row.get("RawProductTitle"))
        linked_brand = clean(row.get("BrandName"))
        parsed_brand = extract_canonical_brand_name(title, linked_brand)
        effective_brand_id = row.get("BrandId") or brands.get(clean_key(parsed_brand))
        effective_brand = (
            linked_brand
            or parsed_brand
            or raw_brand_candidate(title)
            or "Unknown"
        )
        parsed_model = extract_model_hint(title, parsed_brand or linked_brand)
        linked_model = clean(row.get("LinkedModelName"))

        if row.get("BoardModelId") is None:
            category = ""
            existing_model = ""
            action = ""
            raw_candidate = raw_brand_candidate(title)
            if row.get("BrandId") is None and parsed_brand and brands.get(clean_key(parsed_brand)):
                category = "alias_failure"
                action = f"Map retailer brand alias to {parsed_brand}"
                remediation[(category, action)] += 1
            elif effective_brand_id is None:
                category = "unknown_brand_or_alias_failure"
                action = f"Review brand alias: {raw_candidate or effective_brand}"
                remediation[(category, action)] += 1
            else:
                catalogue_models = models_by_brand.get(effective_brand_id, [])
                status, existing_model = closest_model_status(parsed_model, catalogue_models)
                parse_reason = parser_failure_reason(parsed_model, title)
                if status:
                    category = status
                    action = f"Link {effective_brand} / {parsed_model} to {existing_model}"
                elif parse_reason:
                    category = f"parsing_failure:{parse_reason}"
                    action = f"Add parser rule for {parse_reason}"
                else:
                    category = "genuine_new_model_absent_from_catalogue"
                    action = f"Add BoardModel: {effective_brand} / {parsed_model}"
                remediation[(category, action)] += 1

            key = (effective_brand, parsed_model or "Unparsed", category, existing_model, action)
            entry = model_groups.setdefault(key, {
                "brand": effective_brand,
                "model": parsed_model or "Unparsed",
                "category": category,
                "classification": remediation_classification(category),
                "existingCanonicalModel": existing_model or None,
                "recommendedAction": action,
                "count": 0,
                "retailers": Counter(),
                "sampleTitles": [],
            })
            entry["count"] += 1
            entry["retailers"][clean(row.get("RetailerName"))] += 1
            if title not in entry["sampleTitles"] and len(entry["sampleTitles"]) < 3:
                entry["sampleTitles"].append(title)
            category_counts[category] += 1

        if row.get("BoardSizeId") is None:
            length = clean(row.get("LengthFeetInches"))
            volume = decimal_or_none(row.get("VolumeLitres"))
            size_category = ""
            size_action = ""
            if row.get("BoardModelId") is None:
                size_category = "blocked_by_missing_model"
                size_action = f"Resolve model first: {effective_brand} / {parsed_model or 'Unparsed'}"
            elif not length:
                size_category = "parsing_failure:missing_length"
                size_action = "Improve length parsing"
            else:
                same_length = [
                    size for size in sizes_by_model.get(row["BoardModelId"], [])
                    if clean(size.get("lengthFeetInches")) == length
                ]
                if not same_length:
                    size_category = "genuine_new_size_absent_from_catalogue"
                    size_action = f"Add BoardSize: {effective_brand} / {linked_model} / {length}"
                elif volume is None:
                    size_category = (
                        "unique_existing_size_not_linked"
                        if len(same_length) == 1
                        else "ambiguous_existing_sizes_missing_volume"
                    )
                    size_action = "Link unique size" if len(same_length) == 1 else "Capture retailer volume"
                else:
                    deltas = []
                    for size in same_length:
                        canonical_volume = decimal_or_none(size.get("volumeLitres"))
                        if canonical_volume is not None:
                            deltas.append(abs(volume - canonical_volume))
                    minimum = min(deltas) if deltas else None
                    if minimum is not None and minimum <= decimal_or_none("0.20"):
                        size_category = "existing_size_within_tolerance_not_linked"
                        size_action = "Review ambiguous or duplicate canonical sizes"
                    else:
                        size_category = "genuine_new_size_volume_absent_from_catalogue"
                        size_action = f"Add BoardSize volume: {effective_brand} / {linked_model} / {length} / {volume}L"
            remediation[(size_category, size_action)] += 1
            size_category_counts[size_category] += 1
            key = (
                effective_brand,
                linked_model or parsed_model or "Unparsed",
                length or "Missing",
                str(volume) if volume is not None else "Missing",
                size_category,
                size_action,
            )
            entry = size_groups.setdefault(key, {
                "brand": effective_brand,
                "model": linked_model or parsed_model or "Unparsed",
                "lengthFeetInches": length or None,
                "volumeLitres": float(volume) if volume is not None else None,
                "category": size_category,
                "recommendedAction": size_action,
                "count": 0,
                "retailers": Counter(),
                "sampleTitles": [],
            })
            entry["count"] += 1
            entry["retailers"][clean(row.get("RetailerName"))] += 1
            if title not in entry["sampleTitles"] and len(entry["sampleTitles"]) < 3:
                entry["sampleTitles"].append(title)

    def serialise(entries: dict[tuple, dict]) -> list[dict]:
        output = []
        for entry in entries.values():
            output.append({
                **entry,
                "retailers": dict(entry["retailers"].most_common()),
            })
        return sorted(output, key=lambda item: (-item["count"], item["brand"], item["model"]))

    all_missing_models = serialise(model_groups)
    missing_models = all_missing_models[:250]
    missing_sizes = serialise(size_groups)[:250]
    ranked_remediation = [
        {"category": key[0], "recommendedAction": key[1], "potentialRowsUnlocked": count}
        for key, count in remediation.most_common(500)
    ]
    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only",
        "regionCode": "EU",
        "sqlWrites": 0,
        "incompleteEuRows": len(rows),
        "rowsMissingBoardModelId": sum(row.get("BoardModelId") is None for row in rows),
        "rowsMissingBoardSizeId": sum(row.get("BoardSizeId") is None for row in rows),
        "modelCategoryCounts": dict(category_counts.most_common()),
        "sizeCategoryCounts": dict(size_category_counts.most_common()),
        "brandAliasesCompared": len(BRAND_ALIASES),
        "estimatedAdditionalLinksFromParser": {
            "brandLinks": len(linker_dry_run["brandUpdates"]),
            "modelLinks": len(linker_dry_run["modelUpdates"]),
            "sizeLinks": len(linker_dry_run["sizeUpdates"]),
        },
        "estimatedModelLinksFromCatalogueExpansion": category_counts[
            "genuine_new_model_absent_from_catalogue"
        ],
        "missingModelsRanked": all_missing_models,
        "top250MissingModels": missing_models,
        "top250MissingSizes": missing_sizes,
        "rankedRemediation": ranked_remediation,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(OUTPUT_MODELS_CSV, missing_models)
    write_csv(OUTPUT_ALL_MODELS_CSV, all_missing_models)
    write_csv(OUTPUT_SIZES_CSV, missing_sizes)
    print(f"Incomplete EU rows: {report['incompleteEuRows']}")
    print(f"Missing BoardModelId: {report['rowsMissingBoardModelId']}")
    print(f"Missing BoardSizeId: {report['rowsMissingBoardSizeId']}")
    print(f"Report: {output_path}")


if __name__ == "__main__":
    main()
