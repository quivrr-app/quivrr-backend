from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.dealers import build_au_coverage_factory_report as coverage_report  # noqa: E402
from scrapers.retailers.discovery.engine import build_discovery_report  # noqa: E402


OUTPUT_FILE = REPO_ROOT / "scripts" / "dealers" / "output" / "au_retailer_discovery_report.json"
DISCOVERY_ELIGIBLE_STATUSES = {
    "manual_review",
    "ready_shopify",
    "ready_woocommerce",
    "ready_bigcommerce",
    "ready_neto_maropost",
    "ready_opencart",
    "ready_custom_high_value",
    "blocked",
}


def select_candidates(limit: int | None = None) -> list[dict]:
    rows = coverage_report.build_candidate_rows(include_discovery=False)
    eligible = [row for row in rows if row["status"] in DISCOVERY_ELIGIBLE_STATUSES]
    if limit:
        eligible = eligible[:limit]
    return [
        {
            "dealerName": row["dealerName"],
            "website": row["website"],
            "status": row["status"],
        }
        for row in eligible
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the AU retailer discovery engine and write a local-only structured report."
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional candidate cap for a smaller local run.")
    args = parser.parse_args()

    candidates = select_candidates(limit=max(0, args.limit) or None)
    report = build_discovery_report(candidates)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("AU retailer discovery complete")
    print(f"Candidates analysed: {report['candidateCount']}")
    for status, count in sorted(report["summary"].items()):
        print(f"{status}: {count}")
    print(f"Report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
