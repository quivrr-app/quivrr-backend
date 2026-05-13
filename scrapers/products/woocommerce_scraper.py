import json
import requests
from pathlib import Path


INPUT_FILE = Path("scrapers/retailers/active_scrape_targets.json")
OUTPUT_DIR = Path("scrapers/products/output/woocommerce")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 QuivrrBot/1.0"
}

PER_PAGE = 100


def safe_filename(value):
    return (
        str(value)
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("&", "and")
        .replace("'", "")
        .replace('"', "")
    )


def clear_existing_outputs():
    for file_path in OUTPUT_DIR.glob("*.json"):
        file_path.unlink()


def extract_products(products, retailer):
    output = []

    for product in products:
        images = product.get("images", [])
        image_urls = [
            image.get("src")
            for image in images
            if image.get("src")
        ]

        attributes = product.get("attributes", [])

        variant_text = " ".join(
            str(attribute.get("option", ""))
            for attribute in attributes
            if attribute.get("option")
        )

        stock_status = product.get("stock_status")
        is_purchasable = product.get("is_purchasable")

        output.append({
            "retailer": retailer["primary_name"],
            "website": retailer["website"],
            "platform": retailer["platform"],
            "product_id": product.get("id"),
            "variant_id": None,
            "title": product.get("name"),
            "handle": product.get("slug"),
            "vendor": "",
            "product_type": "",
            "variant_title": variant_text,
            "price": product.get("price"),
            "compare_at_price": product.get("regular_price"),
            "available": (
                stock_status == "instock"
                or is_purchasable is True
            ),
            "sku": product.get("sku"),
            "product_url": product.get("permalink"),
            "images": image_urls,
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
                headers=HEADERS,
            )

            if response.status_code != 200:
                print(f"  FAILED page {page}: {response.status_code}")
                break

            products = response.json()

            if not products:
                break

            print(f"  Page {page}: {len(products)} products")

            all_products.extend(
                extract_products(products, retailer)
            )

            if len(products) < PER_PAGE:
                break

            page += 1

        except Exception as exc:
            print(f"  ERROR page {page}: {exc}")
            break

    print(f"  Total products: {len(all_products)}")

    return all_products


def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    woocommerce_retailers = [
        retailer
        for retailer in retailers
        if retailer.get("platform") == "woocommerce"
    ]

    print(f"WooCommerce retailers: {len(woocommerce_retailers)}")
    print("")

    clear_existing_outputs()

    total_products = 0

    for index, retailer in enumerate(woocommerce_retailers, start=1):
        print(f"[{index}/{len(woocommerce_retailers)}] {retailer['primary_name']}")

        products = scrape_woocommerce(retailer)
        total_products += len(products)

        output_file = OUTPUT_DIR / f"{safe_filename(retailer['primary_name'])}.json"

        output_file.write_text(
            json.dumps(products, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print("")
    print(f"Total extracted products: {total_products}")


if __name__ == "__main__":
    main()