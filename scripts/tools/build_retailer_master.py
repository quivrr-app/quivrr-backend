import json
from pathlib import Path


AUDIT_FILE = Path("scrapers/products/output/retailer_governance_audit.json")
OUTPUT_FILE = Path("scrapers/retailers/retailer_master.json")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    audit = load_json(AUDIT_FILE)
    rows = audit.get("retailers", [])

    master = []

    for row in rows:
        status = row.get("governance_status")

        master.append({
            "retailerSlug": row.get("retailer_slug"),
            "retailerName": row.get("retailer_name"),
            "website": row.get("website"),
            "platform": row.get("platform"),
            "regionCode": "AU",
            "enabled": status == "production",
            "governanceStatus": status,
            "governanceReason": row.get("governance_reason"),
            "approvedLogoFile": row.get("approved_logo_file") or "",
            "logoPath": f"/assets/retailers/{row.get('approved_logo_file')}" if row.get("approved_logo_file") else "",
            "availableInventory": row.get("available_inventory"),
            "verifiedSurfboards": row.get("verified_surfboards"),
            "rawProducts": row.get("raw_products"),
        })

    OUTPUT_FILE.write_text(
        json.dumps(master, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    enabled = [r for r in master if r["enabled"]]
    disabled = [r for r in master if not r["enabled"]]

    print("")
    print("Retailer master data generated")
    print("=" * 70)
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Total retailers: {len(master)}")
    print(f"Enabled production retailers: {len(enabled)}")
    print(f"Disabled or review retailers: {len(disabled)}")

    print("")
    print("Enabled retailers")
    for row in enabled:
        print(f"- {row['retailerName']} | {row['platform']} | {row['approvedLogoFile']}")

    print("")
    print("Disabled or review retailers")
    for row in disabled:
        print(f"- {row['retailerName']} | {row['governanceStatus']} | {row['governanceReason']}")


if __name__ == "__main__":
    main()
