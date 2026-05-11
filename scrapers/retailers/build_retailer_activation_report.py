from pathlib import Path
import json
from collections import Counter

INPUT_FILE = Path(
    "scrapers/retailers/retailer_scrape_targets_classified.json"
)

OUTPUT_FILE = Path(
    "scrapers/retailers/retailer_activation_report.json"
)


def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    summary = Counter()

    activation = []

    for r in retailers:
        ecommerce = r.get("ecommerce_platform")
        country = r.get("country")
        active = r.get("active", True)

        if country != "Australia":
            continue

        summary["total_au"] += 1

        if ecommerce:
            summary[f"platform_{ecommerce.lower()}"] += 1
        else:
            summary["platform_unknown"] += 1

        activation.append({
            "name": r.get("name"),
            "website": r.get("website"),
            "platform": ecommerce,
            "active": active,
            "priority": (
                "high"
                if ecommerce in ["Shopify", "WooCommerce"]
                else "medium"
            )
        })

    activation = sorted(
        activation,
        key=lambda x: (
            x["priority"] != "high",
            x["platform"] or "",
            x["name"] or ""
        )
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            {
                "summary": dict(summary),
                "retailers": activation
            },
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("\nAustralian retailer activation report")
    print("=" * 60)

    for k, v in summary.items():
        print(f"{k}: {v}")

    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
    