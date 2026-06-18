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


REGION_CODE = "EU"
PRIORITY_RETAILERS = {
    "58_surf": "58 Surf",
    "surf_boss": "Surf Boss",
    "pukas_surf_shop": "Pukas Surf Shop",
    "bell_surf": "Bell Surf",
}
DISCOVERY_FILES = [
    Path("scrapers/retailers/europe/shopify/output/eu_shopify_product_discovery.json"),
    Path("scrapers/retailers/europe/magento/output/eu_magento_product_discovery.json"),
    Path("scrapers/retailers/europe/woocommerce/output/eu_woocommerce_product_discovery.json"),
]
NORMALISED_FILE = Path("scrapers/retailers/europe/output/eu_normalised_inventory.json")
IMPORT_REPORT_FILE = Path("scripts/europe/output/eu_retailer_import_dry_run_report.json")
OUTPUT_FILE = Path("scripts/europe/output/eu_retailer_inventory_audit.json")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def discovery_counts() -> dict[str, dict]:
    counts: dict[str, dict] = {}
    for path in DISCOVERY_FILES:
        for result in load_json(path).get("results", []):
            slug = result.get("target")
            if slug not in PRIORITY_RETAILERS:
                continue
            accepted = int(result.get("productsAccepted", 0))
            rejected = int(result.get("productsRejected", 0))
            diagnostics = result.get("diagnostics", {})
            counts[slug] = {
                "fetchedProducts": int(
                    diagnostics.get("rawFetched", accepted + rejected)
                ),
                "uniqueProducts": int(
                    diagnostics.get("uniqueProducts", accepted + rejected)
                ),
                "likelySurfboards": int(
                    diagnostics.get("likelySurfboards", accepted)
                ),
                "normalisedRows": diagnostics.get("normalisedRows"),
                "missingDimensions": diagnostics.get("missingDimensions"),
                "importableRows": diagnostics.get("importableRows"),
                "fetches": result.get("fetches", []),
            }
    return counts


def normalised_counts() -> Counter:
    rows = load_json(NORMALISED_FILE).get("rows", [])
    return Counter(
        row.get("retailerSlug")
        for row in rows
        if row.get("regionCode") == REGION_CODE
    )


def import_counts(path: Path) -> dict[str, dict]:
    return load_json(path).get("perRetailerDiagnostics", {})


def sql_counts() -> tuple[dict, dict[str, dict]]:
    from sqlalchemy import text

    from scripts.europe.import_eu_retailer_inventory import (
    build_engine,
    connect_with_retry,
        count_inventory_by_region,
        count_retailers_by_region,
    )

    engine = build_engine()
    with connect_with_retry(engine) as conn:
        regions = {
            region: {
                "inventoryRows": count_inventory_by_region(conn, region),
                "retailerRows": count_retailers_by_region(conn, region),
            }
            for region in ("AU", "ID", "EU")
        }
        rows = conn.execute(
            text("""
                SELECT
                    r.RetailerName,
                    COUNT(ri.InventoryId) AS ImportRows,
                    SUM(CASE WHEN ri.BoardModelId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedModels,
                    SUM(CASE WHEN ri.BoardSizeId IS NOT NULL THEN 1 ELSE 0 END) AS LinkedSizes
                FROM dbo.Retailers r
                LEFT JOIN dbo.RetailerInventory ri
                  ON ri.RetailerId = r.RetailerId
                 AND ri.RegionCode = 'EU'
                WHERE r.RegionCode = 'EU'
                GROUP BY r.RetailerName
            """),
        ).fetchall()
    by_name = {
        row.RetailerName: {
            "sqlImportRows": int(row.ImportRows or 0),
            "linkedBoardModelIdRows": int(row.LinkedModels or 0),
            "linkedBoardSizeIdRows": int(row.LinkedSizes or 0),
        }
        for row in rows
    }
    return regions, by_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit priority EU retailer ingestion without SQL writes.")
    parser.add_argument("--import-report", default=str(IMPORT_REPORT_FILE))
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    parser.add_argument("--sql-read-only", action="store_true")
    parser.add_argument("--expected-au", type=int)
    parser.add_argument("--expected-id", type=int)
    args = parser.parse_args()

    discovery = discovery_counts()
    normalised = normalised_counts()
    imports = import_counts(Path(args.import_report))
    regions = {}
    sql_by_name = {}
    if args.sql_read_only:
        regions, sql_by_name = sql_counts()

    diagnostics = {}
    for slug, name in PRIORITY_RETAILERS.items():
        fetch = discovery.get(slug, {})
        imported = imports.get(slug, {})
        linked = sql_by_name.get(name, {})
        diagnostics[slug] = {
            "retailerName": name,
            "fetchedProducts": fetch.get("fetchedProducts", 0),
            "uniqueProducts": fetch.get("uniqueProducts", 0),
            "likelySurfboards": fetch.get("likelySurfboards", 0),
            "normalisedSurfboards": (
                fetch.get("normalisedRows")
                if fetch.get("normalisedRows") is not None
                else normalised[slug]
            ),
            "missingDimensions": fetch.get("missingDimensions"),
            "importRows": (
                fetch.get("importableRows")
                if fetch.get("importableRows") is not None
                else imported.get("importRows", 0)
            ),
            "linkedBoardModelIdRows": linked.get("linkedBoardModelIdRows", 0),
            "linkedBoardSizeIdRows": linked.get("linkedBoardSizeIdRows", 0),
            "parserDiagnostics": imported.get("rejectReasonCounts", {}),
            "fetches": fetch.get("fetches", []),
        }

    if args.expected_au is not None and regions.get("AU", {}).get("inventoryRows") != args.expected_au:
        raise RuntimeError("AU inventory count changed during EU validation.")
    if args.expected_id is not None and regions.get("ID", {}).get("inventoryRows") != args.expected_id:
        raise RuntimeError("ID inventory count changed during EU validation.")

    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_sql" if args.sql_read_only else "files_only",
        "regionCode": REGION_CODE,
        "priorityRetailers": diagnostics,
        "sqlRegionCounts": regions,
        "safety": {
            "sqlWrites": 0,
            "auExpected": args.expected_au,
            "idExpected": args.expected_id,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("EU retailer inventory audit complete")
    for slug, item in diagnostics.items():
        print(
            f"{slug}: fetched={item['fetchedProducts']} likely={item['likelySurfboards']} "
            f"normalised={item['normalisedSurfboards']} import={item['importRows']} "
            f"model_links={item['linkedBoardModelIdRows']} size_links={item['linkedBoardSizeIdRows']} "
            f"diagnostics={item['parserDiagnostics']}"
        )
    if regions:
        print(
            "Regional inventory counts: "
            + ", ".join(f"{region}={values['inventoryRows']}" for region, values in regions.items())
        )
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
