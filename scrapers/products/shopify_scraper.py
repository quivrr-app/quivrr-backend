import json
import requests
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets_classified.json")
OUTPUT_DIR = Path("scrapers/products/output/shopify")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 QuivrrBot/0.1"
}

def extract_products(products, retailer):
    output = []

    for product in products:
        variants = product.get("variants", [])
        images = product.get("images", [])

        image_urls = [img.get("src") for img in images if img.get("src")]

        for variant in variants:
            output.append({
                "retailer": retailer["primary_name"],
                "website": retailer["website"],
                "platform": retailer["platform"],

                "product_id": product.get("id"),
                "variant_id": variant.get("id"),

                "title": product.get("title"),
                "handle": product.get("handle"),
                "vendor": product.get("vendor"),
                "product_type": product.get("product_type"),

                "variant_title": variant.get("title"),

                "price": variant.get("price"),
                "compare_at_price": variant.get("compare_at_price"),

                "available": variant.get("available"),

                "sku": variant.get("sku"),

                "product_url": f"{retailer['website'].rstrip('/')}/products/{product.get('handle')}",

                "images": image_urls
            })

    return output

def scrape_shopify(retailer):
    base = retailer["website"].rstrip("/")
    page = 1
    all_products = []

    print(f"Scraping: {retailer['primary_name']}")

    while True:
        url = f"{base}/products.json?limit=250&page={page}"

        try:
            response = requests.get(
                url,
                timeout=30,
                headers=HEADERS
            )

            if response.status_code != 200:
                print(f"  FAILED page {page}: {response.status_code}")
                break

            data = response.json()
            products = data.get("products", [])

            if not products:
                break

            print(f"  Page {page}: {len(products)} products")
            all_products.extend(products)

            if len(products) < 250:
                break

            page += 1

        except Exception as exc:
            print(f"  ERROR page {page}: {exc}")
            break

    print(f"  Total products: {len(all_products)}")

    return extract_products(all_products, retailer)

def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    shopify_retailers = [
        r for r in retailers
        if r.get("platform") == "shopify"
    ]

    print(f"Shopify retailers: {len(shopify_retailers)}")
    print("")

    total_products = 0

    for retailer in shopify_retailers:
        products = scrape_shopify(retailer)

        total_products += len(products)

        filename = (
            retailer["primary_name"]
            .lower()
            .replace(" ", "_")
            .replace("/", "_")
        )

        output_file = OUTPUT_DIR / f"{filename}.json"

        output_file.write_text(
            json.dumps(products, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    print("")
    print(f"Total extracted products: {total_products}")

if __name__ == "__main__":
    main()