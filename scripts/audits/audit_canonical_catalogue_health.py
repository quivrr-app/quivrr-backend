from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from audits.canonical_catalogue_health import build_canonical_catalogue_health_report


def main() -> None:
    report = build_canonical_catalogue_health_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print()
    print("Canonical Catalogue Health")
    print("==========================")
    for brand in report.get("brands", []):
        print(
            f"{brand['brandName']}: models={brand['canonicalModelCount']} "
            f"sizes={brand['canonicalSizeCount']} dropdown={brand['dropdownModelCount']} "
            f"missingSizes={len(brand.get('modelsWithNoSizes', []))} "
            f"indicators={','.join(brand.get('suspiciousModelLossIndicators', [])) or 'none'}"
        )


if __name__ == "__main__":
    main()

