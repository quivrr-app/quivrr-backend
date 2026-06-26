from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from audits.regional_availability_health import build_regional_availability_health_report


def main() -> None:
    report = build_regional_availability_health_report()
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print()
    print("Regional Availability Health")
    print("============================")
    for row in report.get("regions", []):
        print(
            f"{row['region']} {row['brandName']}: "
            f"retailerActive={row['retailerActiveRows']} retailerAvailable={row['retailerAvailableRows']} "
            f"mfaActive={row['manufacturerActiveRows']} fallbackEligible={row['fallbackEligibleRows']} "
            f"closeEligible={row['closeEligibleRows']}"
        )


if __name__ == "__main__":
    main()

