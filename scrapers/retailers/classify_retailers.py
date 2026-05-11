from pathlib import Path
import json
import requests

INPUT_FILE = Path(
    "scrapers/retailers/retailer_seed_expanded_enriched.json"
)

OUTPUT_FILE = Path(
    "scrapers/retailers/retailer_scrape_targets_classified.json"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def detect_platform(html, headers):
    html_lower = html.lower()

    if "cdn.shopify.com" in html_lower:
        return "Shopify"

    if "shopify.theme" in html_lower:
        return "Shopify"

    if "woocommerce" in html_lower:
        return "WooCommerce"

    if "wp-content/plugins/woocommerce" in html_lower:
        return "WooCommerce"

    if "bigcommerce" in html_lower:
        return "BigCommerce"

    if "squarespace" in html_lower:
        return "Squarespace"

    server = headers.get("server", "").lower()

    if "shopify" in server:
        return "Shopify"

    return None


def classify(retailer):
    website = retailer.get("website")

    if not website:
        retailer["ecommerce_platform"] = None
        retailer["platform_detection_status"] = "missing_website"
        return retailer

    try:
        response = requests.get(
            website,
            headers=HEADERS,
            timeout=20
        )

        platform = detect_platform(
            response.text,
            response.headers
        )

        retailer["ecommerce_platform"] = platform
        retailer["platform_detection_status"] = "ok"
        retailer["http_status"] = response.status_code

    except Exception as e:
        retailer["ecommerce_platform"] = None
        retailer["platform_detection_status"] = str(e)

    return retailer


def main():
    retailers = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    classified = []

    for idx, retailer in enumerate(retailers, start=1):
        name = retailer.get("name")

        print(f"[{idx}/{len(retailers)}] {name}")

        classified.append(
            classify(retailer)
        )

    OUTPUT_FILE.write_text(
        json.dumps(
            classified,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("\nRetailer classification complete")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
