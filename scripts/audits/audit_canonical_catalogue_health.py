from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from audits.canonical_catalogue_health import build_canonical_catalogue_health_report

OUTPUT_FILE = ROOT / "scripts" / "output" / "canonical_catalogue_audit.json"


def main() -> None:
    report = build_canonical_catalogue_health_report()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print()
    print("Canonical Catalogue Health")
    print("==========================")
    for brand in report.get("brands", []):
        print(
            f"{brand['brandName']}: official={brand.get('officialModelCount', 0)} "
            f"canonical={brand['canonicalModelCount']} "
            f"sizes={brand['canonicalSizeCount']} dropdown={brand['dropdownModelCount']} "
            f"missingOfficial={len(brand.get('officialModelsMissingFromCanonical', []))} "
            f"aliases={len(brand.get('aliasCandidates', []))} "
            f"retiredCandidates={len(brand.get('retiredCanonicalCandidates', []))} "
            f"indicators={','.join(brand.get('suspiciousModelLossIndicators', [])) or 'none'}"
        )
    print()
    print(f"Audit file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
