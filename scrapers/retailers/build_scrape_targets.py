import json
from pathlib import Path
from urllib.parse import urlparse

INPUT_FILE = Path("scrapers/retailers/retailer_seed_expanded_enriched.json")
OUTPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets.json")

def normalise_url(url):
    url = (url or "").strip()
    if not url:
        return ""

    parsed = urlparse(url)

    domain = parsed.netloc.lower()
    domain = domain.replace("www.", "")

    scheme = parsed.scheme or "https"

    return f"{scheme}://{domain}"

def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    targets = {}

    for item in retailers:
        website = normalise_url(item.get("website", ""))

        if not website:
            continue

        if website not in targets:
            targets[website] = {
                "website": website,
                "country": "Australia",
                "hardboards": True,
                "priority": item.get("priority", 3),
                "retailer_names": [],
                "states": [],
                "region_clusters": [],
                "retailer_types": [],
                "source_brands": [],
                "verification_statuses": []
            }

        target = targets[website]

        target["retailer_names"].append(item.get("name", ""))

        if item.get("state"):
            target["states"].append(item.get("state"))

        if item.get("region_cluster"):
            target["region_clusters"].append(item.get("region_cluster"))

        if item.get("retailer_type"):
            target["retailer_types"].append(item.get("retailer_type"))

        if item.get("verification_status"):
            target["verification_statuses"].append(item.get("verification_status"))

        for brand in item.get("source_brands", []):
            target["source_brands"].append(brand)

        target["priority"] = min(target["priority"], item.get("priority", 3))

    output = []

    for target in targets.values():
        for field in [
            "retailer_names",
            "states",
            "region_clusters",
            "retailer_types",
            "source_brands",
            "verification_statuses"
        ]:
            target[field] = sorted(list(set([v for v in target[field] if v])))

        target["primary_name"] = target["retailer_names"][0] if target["retailer_names"] else ""

        output.append(target)

    output.sort(key=lambda x: (x["priority"], x["primary_name"].lower()))

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Input retailer records: {len(retailers)}")
    print(f"Unique scrape targets: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
