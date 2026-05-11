import json
import requests
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/retailer_scrape_targets_classified.json")
OUTPUT_DIR = Path("scrapers/products/output/woocommerce")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 QuivrrBot/0.1"
}

PER_PAGE = 100

def extract_products(products, retailer):
    output = []

    for product in products:

        images = product.get("images", [])
        image_urls = [img.get("src") for img in images if img.get("src")]

        attributes = product.get("attributes", [])

        variant_text = " ".join(
            [
                str(a.get("option", ""))
                for a in attributes
            ]
        )

        output.append({
            "retailer": retailer["primary_name"],
            "website": retailer["website"],
            "platform": retailer["platform"],

            "product_id": product.get("id"),

            "title": product.get("name"),
            "handle": product.get("slug"),
            "vendor": "",

            "product_type": "",

            "variant_title": variant_text,

            "price": product.get("price"),
            "compare_at_price": product.get("regular_price"),

            "available": (
                product.get("stock_status") == "instock"
            ),

            "sku": product.get("sku"),

            "product_url": product.get("permalink"),

            "images": image_urls
        })

    return output

def scrape_woocommerce(retailer):

    base = retailer["website"].rstrip("/")

    page = 1
    all_products = []

    print(f"Scraping: {retailer['primary_name']}")

    while True:

        url = (
            f"{base}/wp-json/wc/store/products"
            f"?page={page}"
            f"&per_page={PER_PAGE}"
        )

        try:

            response = requests.get(
                url,
                timeout=30,
                headers=HEADERS
            )

            if response.status_code != 200:
                print(f"  FAILED {response.status_code}")
                break

            products = response.json()

            if not products:
                break

            print(f"  Page {page}: {len(products)} products")

            extracted = extract_products(products, retailer)

            all_products.extend(extracted)

            if len(products) < PER_PAGE:
                break

            page += 1

        except Exception as exc:
            print(f"  ERROR: {exc}")
            break

    print(f"  Total products: {len(all_products)}")

    return all_products

def main():

    retailers = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    woocommerce_retailers = [
        r for r in retailers
        if r.get("platform") == "woocommerce"
    ]

    print(f"WooCommerce retailers: {len(woocommerce_retailers)}")
    print("")

    total_products = 0

    for retailer in woocommerce_retailers:

        products = scrape_woocommerce(retailer)

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