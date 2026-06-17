from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.europe.import_eu_retailer_inventory import (  # noqa: E402
    build_canonical_link_report,
    build_engine,
    count_inventory_by_region,
    priority_retailer_counts,
    public_link_report,
)


OUTPUT_FILE = Path("scripts/europe/output/eu_canonical_link_audit.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only EU canonical link audit.")
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    args = parser.parse_args()

    with build_engine().connect() as conn:
        region_counts = {
            region: count_inventory_by_region(conn, region)
            for region in ("AU", "ID", "EU")
        }
        retailer_counts = priority_retailer_counts(conn)
        report = public_link_report(build_canonical_link_report(conn))

    reasons = Counter()
    for row in report.get("unlinkedRowSample", []):
        reasons.update(row.get("reasons", []))

    output = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only",
        "regionCode": "EU",
        "regionCounts": region_counts,
        "retailerCounts": retailer_counts,
        "linkAudit": report,
        "topRemainingReasons": [
            {"reason": reason, "countInSample": count}
            for reason, count in reasons.most_common()
        ],
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    total = report["totalEuRows"]
    models = report["linkedModels"]
    sizes = report["linkedSizes"]
    print("EU canonical link audit complete")
    print(f"EU rows: {total}")
    print(f"BoardModelId linked: {models} ({models / total:.1%})")
    print(f"BoardSizeId linked: {sizes} ({sizes / total:.1%})")
    for retailer in report.get("retailerAudit", []):
        print(retailer)
    print(f"Brand link candidates: {report['brandLinkCandidates']}")
    print(f"Model link candidates: {report['modelLinkCandidates']}")
    print(f"Size link candidates: {report['sizeLinkCandidates']}")
    print(f"Report: {path}")


if __name__ == "__main__":
    main()
