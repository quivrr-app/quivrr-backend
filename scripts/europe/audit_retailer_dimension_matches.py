"""Read-only cross-brand audit for regional retailer exact-match policy."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import bindparam, text


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from utils.dimensions import length_to_inches, measurements_within  # noqa: E402
from utils.retailer_matching import classify_retailer_exact  # noqa: E402


BRANDS = (
    "Lost",
    "Channel Islands",
    "Rusty",
    "JS Industries",
    "Pyzel",
    "Firewire",
    "DHD",
    "Haydenshapes",
    "Sharp Eye",
)


def legacy_exact(row: dict, canonical: dict) -> tuple[bool, str]:
    if not app.model_name_matches(row["title"], row["normalisedTitle"], row["modelName"]):
        return False, "legacy_title_model_mismatch"
    if row["length"] != canonical["length"]:
        return False, "legacy_length_string_mismatch"
    if canonical["construction"]:
        row_construction = str(row["construction"] or "").strip().lower()
        canonical_construction = str(canonical["construction"] or "").strip().lower()
        title = f"{row['title']} {row['normalisedTitle']}".lower()
        ci_title_match = (
            row["brandName"] == "Channel Islands"
            and (
                (canonical_construction in {"ect-carbon", "ect carbon"} and "ect" in title)
                or (
                    canonical_construction in {"spine-tek", "spine tek", "spinetek"}
                    and "spine" in title
                )
            )
        )
        if row_construction != canonical_construction and not ci_title_match:
            return False, "legacy_construction_missing_or_mismatch"
    if row["volume"] is not None and canonical["volume"] is not None:
        if not measurements_within(row["volume"], canonical["volume"], "0.75"):
            return False, "legacy_volume_outside_tolerance"
    return True, "legacy_exact"


def legacy_close(row: dict, canonical: dict) -> bool:
    if not app.model_family_matches(row["title"], row["normalisedTitle"], row["modelName"]):
        return False
    left = length_to_inches(row["length"] or row["title"])
    right = length_to_inches(canonical["length"])
    if left is None or right is None or abs(left - right) > 1:
        return False
    return (
        row["volume"] is None
        or canonical["volume"] is None
        or measurements_within(row["volume"], canonical["volume"], "2.0")
    )


def audit() -> dict:
    query = text("""
        SELECT
            ri.InventoryId,
            r.RetailerName,
            ri.RawProductTitle,
            ri.NormalisedProductTitle,
            ri.BrandId,
            ri.BoardModelId,
            ri.BoardSizeId,
            ri.LengthFeetInches,
            ri.Width,
            ri.Thickness,
            ri.VolumeLitres,
            ri.Construction,
            b.BrandName,
            bm.ModelName,
            bs.BoardSizeId AS CandidateBoardSizeId,
            bs.LengthFeetInches AS CanonicalLength,
            bs.Width AS CanonicalWidth,
            bs.Thickness AS CanonicalThickness,
            bs.VolumeLitres AS CanonicalVolume,
            bs.Construction AS CanonicalConstruction
        FROM dbo.RetailerInventory ri
        INNER JOIN dbo.Retailers r ON r.RetailerId = ri.RetailerId
        INNER JOIN dbo.Brands b ON b.BrandId = ri.BrandId
        INNER JOIN dbo.BoardModels bm ON bm.BoardModelId = ri.BoardModelId
        INNER JOIN dbo.BoardSizes bs ON bs.BoardModelId = ri.BoardModelId
        WHERE ri.RegionCode = 'EU'
          AND ri.IsActive = 1
          AND b.BrandName IN :brands
    """).bindparams(bindparam("brands", expanding=True))

    rows_by_brand: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for item in app.execute_with_retry(query, {"brands": list(BRANDS)}):
        row = {
            "inventoryId": int(item.InventoryId),
            "retailerName": item.RetailerName,
            "title": item.RawProductTitle or "",
            "normalisedTitle": item.NormalisedProductTitle or "",
            "brandId": item.BrandId,
            "boardModelId": item.BoardModelId,
            "boardSizeId": item.BoardSizeId,
            "brandName": item.BrandName,
            "modelName": item.ModelName,
            "length": item.LengthFeetInches,
            "width": item.Width,
            "thickness": item.Thickness,
            "volume": item.VolumeLitres,
            "construction": item.Construction,
        }
        canonical = {
            "boardSizeId": int(item.CandidateBoardSizeId),
            "length": item.CanonicalLength,
            "width": item.CanonicalWidth,
            "thickness": item.CanonicalThickness,
            "volume": item.CanonicalVolume,
            "construction": item.CanonicalConstruction,
        }
        if length_to_inches(row["length"] or row["title"]) != length_to_inches(canonical["length"]):
            continue
        before, before_reason = legacy_exact(row, canonical)
        after, after_reason = classify_retailer_exact(
            row,
            canonical,
            brand_matches=True,
            model_matches=True,
            strong_model_title=app.text_contains_phrase(
                row["title"], row["normalisedTitle"], row["modelName"]
            ),
        )
        rows_by_brand[item.BrandName][int(item.InventoryId)].append({
            "row": row,
            "canonical": canonical,
            "beforeExact": before,
            "beforeReason": before_reason,
            "beforeClose": legacy_close(row, canonical) and not before,
            "afterExact": after,
            "afterReason": after_reason,
        })

    brands = []
    for brand_name in BRANDS:
        inventory = rows_by_brand[brand_name]
        before_ids = {
            inventory_id for inventory_id, pairs in inventory.items()
            if any(pair["beforeExact"] for pair in pairs)
        }
        after_ids = {
            inventory_id for inventory_id, pairs in inventory.items()
            if any(pair["afterExact"] for pair in pairs)
        }
        samples = []
        for inventory_id, pairs in inventory.items():
            close_pairs = [pair for pair in pairs if pair["beforeClose"]]
            if not close_pairs:
                continue
            pair = sorted(
                close_pairs,
                key=lambda value: (
                    not value["afterExact"],
                    value["canonical"]["boardSizeId"] != value["row"]["boardSizeId"],
                    value["canonical"]["boardSizeId"],
                ),
            )[0]
            samples.append({
                "inventoryId": inventory_id,
                "retailerName": pair["row"]["retailerName"],
                "rawTitle": pair["row"]["title"],
                "modelName": pair["row"]["modelName"],
                "retailerDimensions": {
                    key: pair["row"][key]
                    for key in ("length", "width", "thickness", "volume", "construction")
                },
                "canonicalBoardSizeId": pair["canonical"]["boardSizeId"],
                "canonicalDimensions": {
                    key: pair["canonical"][key]
                    for key in ("length", "width", "thickness", "volume", "construction")
                },
                "whyPreviouslyClose": pair["beforeReason"],
                "afterClassification": "exact" if pair["afterExact"] else "close",
                "afterReason": pair["afterReason"],
            })
        samples.sort(key=lambda value: (value["afterClassification"] != "exact", value["inventoryId"]))
        brands.append({
            "brandName": brand_name,
            "inventoryRowsEvaluated": len(inventory),
            "beforeExactRows": len(before_ids),
            "afterExactRows": len(after_ids),
            "netExactRows": len(after_ids) - len(before_ids),
            "currentlyCloseSamples": samples[:5],
            "sampleShortfall": max(0, 5 - len(samples)),
        })

    return {"regionCode": "EU", "writes": 0, "brands": brands}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scripts/europe/output/regional_dimension_match_audit.json")
    args = parser.parse_args()
    result = audit()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    for brand in result["brands"]:
        print(
            f"{brand['brandName']}: before={brand['beforeExactRows']} "
            f"after={brand['afterExactRows']} net={brand['netExactRows']} "
            f"close_samples={len(brand['currentlyCloseSamples'])}"
        )
    print(f"Read-only report: {output}")


if __name__ == "__main__":
    main()
