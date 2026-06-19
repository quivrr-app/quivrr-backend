from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.europe.import_eu_retailer_inventory import (  # noqa: E402
    build_engine,
    connect_with_retry,
    model_key,
)

INPUT = Path(
    "scrapers/manufacturers/availability/js_industries/output/"
    "js_industries_eu_manufacturer_inventory.json"
)
OUTPUT = Path("scripts/manufacturer_availability/output/js_eu_mfa_diagnostic.json")


def main():
    rows = json.loads(INPUT.read_text(encoding="utf-8"))
    with connect_with_retry(build_engine()) as conn:
        canonical = {
            model_key(row.ModelName): (int(row.BoardModelId), row.ModelName)
            for row in conn.execute(text("""
                SELECT bm.BoardModelId, bm.ModelName
                FROM dbo.BoardModels bm
                JOIN dbo.Brands b ON b.BrandId = bm.BrandId
                WHERE b.BrandName = 'JS Industries'
            """))
        }
        au_models = Counter(
            row.ModelName for row in conn.execute(text("""
                SELECT mi.ModelName
                FROM dbo.ManufacturerInventory mi
                JOIN dbo.Brands b ON b.BrandId = mi.BrandId
                WHERE b.BrandName = 'JS Industries' AND mi.RegionCode = 'AU'
            """))
        )

    diagnostics = []
    linked = 0
    blockers = Counter()
    for row in rows:
        parsed = row.get("modelName")
        match = canonical.get(model_key(parsed))
        if match:
            linked += 1
            blocker = None
        elif not parsed:
            blocker = "parsed_model_empty"
        elif model_key(parsed) in {model_key(name) for name in au_models}:
            blocker = "AU_model_name_not_in_canonical_catalogue"
        else:
            blocker = "model_not_in_canonical_catalogue"
        if blocker:
            blockers[blocker] += 1
        diagnostics.append({
            "rawTitle": row.get("rawProductTitle"),
            "sourceVariantTitle": row.get("sourceVariantTitle"),
            "parsedModel": parsed,
            "parsedLength": row.get("lengthFeetInches"),
            "parsedWidth": row.get("width"),
            "parsedThickness": row.get("thickness"),
            "parsedVolume": row.get("volumeLitres"),
            "parsedConstruction": row.get("construction"),
            "candidateCanonicalModel": match[1] if match else None,
            "blockerReason": blocker,
        })

    diagnostics.sort(key=lambda item: (item["blockerReason"] is None, item["rawTitle"] or ""))
    report = {
        "rows": len(rows),
        "modelLinks": linked,
        "modelLinkPercentage": round(linked * 100 / len(rows), 2) if rows else 0,
        "canonicalModelCount": len(canonical),
        "auMfaRows": sum(au_models.values()),
        "blockers": dict(blockers.most_common()),
        "top100Rows": diagnostics[:100],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "top100Rows"}, indent=2))


if __name__ == "__main__":
    main()
