from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from audits.search_behaviour_matrix import build_search_behaviour_matrix


def main() -> None:
    report = build_search_behaviour_matrix()
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print()
    print("Search Behaviour Matrix")
    print("=======================")
    for row in report.get("cases", []):
        print(
            f"{row['label']}: region={row['region']} boardSizeId={row['boardSizeId']} "
            f"direct={row['directCount']} exact={row['exactCount']} close={row['closeCount']} "
            f"other={row['otherModelCount']} mismatch={row['reasonIfMismatch'] or 'none'}"
        )


if __name__ == "__main__":
    main()

