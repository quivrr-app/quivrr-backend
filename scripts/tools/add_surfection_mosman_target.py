import json
from pathlib import Path

path = Path("scrapers/retailers/active_scrape_targets.json")

targets = json.loads(path.read_text(encoding="utf-8"))

name = "Surfection Mosman"
website = "https://surfectionmosman.com"

handles = [
    "js-industries",
    "dhd",
    "sharpeye",
    "channel-islands",
    "haydenshapes",
    "tolhurst-x-harley-ingleby",
    "chilli",
    "lost",
    "volume",
    "global-surf-industries",
    "ocean-soul",
]

exists = any(
    str(item.get("primary_name", "")).strip().lower() == name.lower()
    or str(item.get("website", "")).rstrip("/").lower() == website.lower()
    for item in targets
)

if not exists:
    targets.append({
        "primary_name": name,
        "website": website,
        "website_key": website,
        "country": "Australia",
        "platform": "shopify",
        "status": "active",
        "priority": 1,
        "collection_handles": handles,
        "locations": [
            {
                "name": name,
                "states": [
                    "NSW"
                ],
                "region_clusters": [
                    "Mosman",
                    "Sydney"
                ],
                "retailer_types": [
                    "multi_brand"
                ],
                "hardboards": True,
                "verification_statuses": [
                    "manual_verified",
                    "shopify_brand_collections_verified"
                ]
            }
        ],
        "source": "manual_final_retailer_onboarding"
    })

path.write_text(
    json.dumps(targets, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("Surfection Mosman added:", not exists)
print("Total targets:", len(targets))
