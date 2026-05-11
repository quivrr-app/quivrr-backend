import json
import requests
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets_classified.json")

SHOPIFY_MARKERS = ["cdn.shopify.com", "shopify.theme", "shopify"]
WOOCOMMERCE_MARKERS = ["woocommerce", "wp-content/plugins/woocommerce"]
NEXTJS_MARKERS = ["__NEXT_DATA__"]
ALGOLIA_MARKERS = ["algolia", "instantsearch"]

def detect_platform(html):
    html_lower = html.lower()

    if any(marker in html_lower for marker in SHOPIFY_MARKERS):
        return "shopify"

    if any(marker in html_lower for marker in WOOCOMMERCE_MARKERS):
        return "woocommerce"

    if any(marker in html_lower for marker in NEXTJS_MARKERS):
        return "nextjs"

    if any(marker in html_lower for marker in ALGOLIA_MARKERS):
        return "algolia"

    return "unknown"

def main():
    targets = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    results = []

    for target in targets:
        url = target["website"]

        print(f"Checking {target['primary_name']}: {url}")

        try:
            response = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 QuivrrBot/0.1"}
            )

            target["status_code"] = response.status_code
            target["platform"] = detect_platform(response.text)
            target["homepage_bytes"] = len(response.text)

            print(f"  {response.status_code} | {target['platform']} | {target['homepage_bytes']} bytes")

        except Exception as exc:
            target["status_code"] = None
            target["platform"] = "error"
            target["error"] = str(exc)

            print(f"  ERROR | {exc}")

        results.append(target)

    OUTPUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print("")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
