import json
from pathlib import Path


TARGET_FILE = Path("scrapers/retailers/active_scrape_targets.json")


NEW_TARGETS = [
    {
        "primary_name": "Slimes Newcastle",
        "website": "https://www.slimesnewcastle.com.au",
        "website_key": "https://www.slimesnewcastle.com.au",
        "country": "Australia",
        "platform": "shopify",
        "status": "active",
        "priority": 1,
        "locations": [
            {
                "name": "Slimes Newcastle",
                "states": [
                    "NSW"
                ],
                "region_clusters": [
                    "Newcastle",
                    "Hunter"
                ],
                "retailer_types": [
                    "multi_brand"
                ],
                "hardboards": True,
                "verification_statuses": [
                    "manual_verified",
                    "shopify_products_verified",
                    "surfboards_collection_verified"
                ]
            }
        ],
        "source": "manual_final_retailer_onboarding"
    },
    {
        "primary_name": "Board Collective",
        "website": "https://boardcollective.com.au",
        "website_key": "https://boardcollective.com.au",
        "country": "Australia",
        "platform": "shopify",
        "status": "active",
        "priority": 1,
        "locations": [
            {
                "name": "Board Collective",
                "states": [
                    "NSW"
                ],
                "region_clusters": [
                    "Online",
                    "Australia"
                ],
                "retailer_types": [
                    "multi_brand"
                ],
                "hardboards": True,
                "verification_statuses": [
                    "manual_verified",
                    "shopify_products_verified",
                    "surfboards_collection_verified"
                ]
            }
        ],
        "source": "manual_final_retailer_onboarding"
    }
]


def normalise_url(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .rstrip("/")
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
    )


targets = json.loads(
    TARGET_FILE.read_text(encoding="utf-8")
)

existing_keys = {
    normalise_url(target.get("website"))
    for target in targets
}

existing_names = {
    str(target.get("primary_name", "")).strip().lower()
    for target in targets
}

added = []
skipped = []

for new_target in NEW_TARGETS:
    website_key = normalise_url(new_target.get("website"))
    name_key = str(new_target.get("primary_name", "")).strip().lower()

    if website_key in existing_keys or name_key in existing_names:
        skipped.append(new_target["primary_name"])
        continue

    targets.append(new_target)
    existing_keys.add(website_key)
    existing_names.add(name_key)
    added.append(new_target["primary_name"])


TARGET_FILE.write_text(
    json.dumps(targets, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print()
print("Active scrape target update complete.")
print("Added:")
for item in added:
    print(" -", item)

print()
print("Skipped:")
for item in skipped:
    print(" -", item)

print()
print("Total active targets:", len(targets))
