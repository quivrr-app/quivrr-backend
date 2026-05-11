import json
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/retailer_seed_expanded.json")
OUTPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_website_enrichment.json")

KNOWN = {
    "Beach Beat Surfboards": "https://www.beachbeat.com.au",
    "Boardriders Coolangatta": "https://www.boardriders.co",
    "Natural Necessity": "https://www.naturalnecessity.com.au",
    "NT Surfboards": "https://www.ntsurfboards.com",
    "Onboard Store - Byron Bay": "https://onboardstore.com.au",
    "Red Herring Surf": "https://www.redherringsurf.com.au",
    "Slimes Boardstore": "https://www.slimes.com.au",
    "Slimes Erina": "https://www.slimes.com.au",
    "Surfboard Empire Coolangatta": "https://www.surfboardempire.com.au",
    "Surfboard Empire Kawana": "https://www.surfboardempire.com.au",
    "Surfboard Empire Kirra": "https://www.surfboardempire.com.au",
    "Surfboard Empire Nobby Beach": "https://www.surfboardempire.com.au",
    "Big Drop Surf": "https://www.bigdropsurf.com.au",
    "Big Surf": "https://www.bigsurf.com.au",
    "Cordingley's Surf": "https://www.cordingleyssurf.com.au",
    "Corner Surf Shop": "https://www.cornersurfshop.com.au",
    "Hollow Surf": "https://www.hollowsurf.com.au",
    "Innertube Surf Shop": "https://www.innertubesurf.com.au"
}

def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    output = []

    for item in data:
        if item.get("website"):
            continue

        name = item["name"]

        output.append({
            "name": name,
            "website": KNOWN.get(name, ""),
            "verification_status": "needs_manual_review" if name not in KNOWN else "prefilled"
        })

    output.sort(key=lambda x: x["name"].lower())

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Missing website records: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
