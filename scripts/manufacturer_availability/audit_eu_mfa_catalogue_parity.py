from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.europe.import_eu_retailer_inventory import (  # noqa: E402
    build_engine,
    connect_with_retry,
    model_key,
    tolerant_model_key,
)

BRANDS = ["JS Industries", "Pyzel", "Firewire", "Haydenshapes", "Rusty", "Sharp Eye", "DHD"]
OUTPUT = Path("scripts/manufacturer_availability/output/eu_mfa_catalogue_parity.json")


def parsing_issue(name: str) -> str | None:
    key = model_key(name)
    patterns = {
        "construction_suffix": r"\b(?:pu|eps|hyfi|carbotune|futureflex|helium|ibolic|volcanic|easy rider|x series)\b",
        "colour_suffix": r"\b(?:white|black|blue|red|green|clear|sand|grey|gray)\b",
        "tail_or_fin_suffix": r"\b(?:squash|swallow|round pin|fcs|fcs 2|futures|thruster)\b",
        "size_left_in_model": r"\b[4-9]\s*(?:ft|feet)\s*\d+\b",
    }
    for reason, pattern in patterns.items():
        if re.search(pattern, key):
            return reason
    return None


def main() -> None:
    with connect_with_retry(build_engine()) as conn:
        canonical_rows = conn.execute(text("""
            SELECT b.BrandName, bm.ModelName
            FROM dbo.BoardModels bm JOIN dbo.Brands b ON b.BrandId=bm.BrandId
            WHERE b.BrandName IN ('JS Industries','Pyzel','Firewire','Haydenshapes','Rusty','Sharp Eye','DHD')
        """)).fetchall()
        inventory_rows = conn.execute(text("""
            SELECT BrandName, RegionCode, ModelName, Construction, LengthFeetInches,
                   BoardModelId, BoardSizeId, SourcePayload
            FROM dbo.ManufacturerInventory
            WHERE BrandName IN ('JS Industries','Pyzel','Firewire','Haydenshapes','Rusty','Sharp Eye','DHD')
              AND RegionCode IN ('AU','EU','ID')
        """)).fetchall()

    canonical = defaultdict(dict)
    for row in canonical_rows:
        canonical[row.BrandName][model_key(row.ModelName)] = row.ModelName
    by_region = defaultdict(Counter)
    rows_by_brand_region = defaultdict(list)
    for row in inventory_rows:
        by_region[(row.BrandName, row.RegionCode)][row.ModelName or "<missing>"] += 1
        rows_by_brand_region[(row.BrandName, row.RegionCode)].append(row)

    report_brands = []
    exceptions = []
    for brand in BRANDS:
        canonical_models = canonical[brand]
        canonical_tolerant = defaultdict(list)
        for key, name in canonical_models.items():
            canonical_tolerant[tolerant_model_key(key)].append(name)
        eu = by_region[(brand, "EU")]
        au = by_region[(brand, "AU")]
        ind = by_region[(brand, "ID")]
        classifications = []
        resolved_names = defaultdict(list)
        for eu_name, count in eu.items():
            key = model_key(eu_name)
            canonical_name = canonical_models.get(key)
            classification = "Exact canonical match" if canonical_name else None
            if not canonical_name:
                aliases = canonical_tolerant.get(tolerant_model_key(eu_name), [])
                if len(aliases) == 1:
                    canonical_name = aliases[0]
                    classification = "Alias of canonical model"
            if not classification:
                issue = parsing_issue(eu_name)
                classification = "Parsing error" if issue else "New model absent from canonical catalogue"
            resolved_names[canonical_name or key].append(eu_name)
            entry = {
                "brand": brand, "euName": eu_name, "canonicalName": canonical_name,
                "classification": classification, "rowCount": count,
                "auName": next((name for name in au if model_key(name) == model_key(canonical_name or eu_name)), None),
                "recommendedFix": (
                    "No change" if classification == "Exact canonical match" else
                    f"Add deterministic alias to {canonical_name}" if classification == "Alias of canonical model" else
                    f"Clean {parsing_issue(eu_name)} from parsed model" if classification == "Parsing error" else
                    "Review for canonical BoardModel addition"
                ),
            }
            classifications.append(entry)
            if classification != "Exact canonical match":
                exceptions.append(entry)
        duplicate_names = {key: names for key, names in resolved_names.items() if len(names) > 1}
        for item in classifications:
            resolved = item["canonicalName"] or model_key(item["euName"])
            if resolved in duplicate_names and item["classification"] != "Exact canonical match":
                item["classification"] = "Duplicate variant representation"
                item["recommendedFix"] = f"Collapse names into {item['canonicalName'] or resolved}"
        matched_rows = sum(item["rowCount"] for item in classifications if item["classification"] in {"Exact canonical match", "Alias of canonical model"})
        eu_rows = sum(eu.values())
        eu_keys = {model_key(name) for name in eu}
        au_keys = {model_key(name) for name in au}
        constructions_eu = {row.Construction for row in rows_by_brand_region[(brand, "EU")] if row.Construction}
        constructions_au = {row.Construction for row in rows_by_brand_region[(brand, "AU")] if row.Construction}
        report_brands.append({
            "brand": brand,
            "canonicalModelCount": len(canonical_models),
            "auModelCount": len(au), "euModelCount": len(eu), "idModelCount": len(ind),
            "euRows": eu_rows,
            "canonicalCoveragePercent": round(100 * matched_rows / eu_rows, 2) if eu_rows else 0,
            "modelsEuNotAu": sorted(name for name in eu if model_key(name) not in au_keys),
            "modelsAuNotEu": sorted(name for name in au if model_key(name) not in eu_keys),
            "constructionOnlyEu": sorted(constructions_eu - constructions_au),
            "constructionOnlyAu": sorted(constructions_au - constructions_eu),
            "duplicateRepresentations": duplicate_names,
            "classifications": classifications,
        })

    pyzel = rows_by_brand_region[("Pyzel", "EU")]
    source_products, source_variants = [], []
    for row in pyzel:
        payload = json.loads(row.SourcePayload) if row.SourcePayload else {}
        source_products.append(str(payload.get("sourceProductId") or ""))
        source_variants.append(str(payload.get("sourceVariantId") or ""))
    result = {
        "mode": "read_only", "sqlWrites": 0,
        "architectureAnswer": "All regions use global BoardModels/BoardSizes; exceptions below are naming, parsing, or catalogue coverage gaps in regional availability rows.",
        "brands": report_brands,
        "rankedExceptions": sorted(exceptions, key=lambda item: (-item["rowCount"], item["brand"], item["euName"])),
        "pyzelRowExplanation": {
            "rows": len(pyzel),
            "distinctModels": len({row.ModelName for row in pyzel}),
            "distinctSizes": len({(row.ModelName, row.LengthFeetInches, row.BoardSizeId) for row in pyzel}),
            "distinctConstructions": len({row.Construction for row in pyzel if row.Construction}),
            "distinctSourceProducts": len({value for value in source_products if value}),
            "distinctSourceVariants": len({value for value in source_variants if value}),
            "duplicateSourceVariantRows": len(source_variants) - len({value for value in source_variants if value}),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"brands": [{k: v for k, v in row.items() if k != "classifications"} for row in report_brands], "pyzel": result["pyzelRowExplanation"], "topExceptions": result["rankedExceptions"][:25]}, indent=2))


if __name__ == "__main__":
    main()
