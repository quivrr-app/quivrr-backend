import json
import requests
from pathlib import Path


INPUT_FILE = Path("scrapers/retailers/active_scrape_targets.json")
OUTPUT_DIR = Path("scrapers/products/output/shopify")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36 QuivrrBot/1.0"
    ),
    "Accept": "application/json,text/html,*/*",
}

PAGE_LIMIT = 250
MAX_PAGES = 80


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


def extract_products(products, retailer):
    output = []

    for product in products:
        variants = product.get("variants", [])
        images = product.get("images", [])

        image_urls = [
            image.get("src")
            for image in images
            if isinstance(image, dict) and image.get("src")
        ]

        for variant in variants:
            handle = product.get("handle")

            output.append({
                "retailer": retailer["primary_name"],
                "website": retailer["website"],
                "platform": retailer["platform"],
                "product_id": product.get("id"),
                "variant_id": variant.get("id"),
                "title": product.get("title"),
                "handle": handle,
                "vendor": product.get("vendor"),
                "product_type": product.get("product_type"),
                "variant_title": variant.get("title"),
                "price": variant.get("price"),
                "compare_at_price": variant.get("compare_at_price"),
                "available": variant.get("available"),
                "sku": variant.get("sku"),
                "product_url": (
                    f"{retailer['website'].rstrip('/')}/products/{handle}"
                    if handle
                    else retailer["website"]
                ),
                "images": image_urls,
            })

    return output


def scrape_shopify(retailer):
    base = retailer["website"].rstrip("/")
    page = 1
    all_products = []
    failed = False

    print(f"Scraping: {retailer['primary_name']}")

    while page <= MAX_PAGES:
        url = f"{base}/products.json?limit={PAGE_LIMIT}&page={page}"

        try:
            response = requests.get(
                url,
                timeout=30,
                headers=HEADERS,
            )

            if response.status_code != 200:
                print(f"  FAILED page {page}: {response.status_code}")
                failed = True
                break

            data = response.json()
            products = data.get("products", [])

            if not products:
                break

            print(f"  Page {page}: {len(products)} products")
            all_products.extend(products)

            if len(products) < PAGE_LIMIT:
                break

            page += 1

        except Exception as exc:
            print(f"  ERROR page {page}: {exc}")
            failed = True
            break

    print(f"  Total products: {len(all_products)}")

    extracted = extract_products(all_products, retailer)

    return {
        "products": extracted,
        "failed": failed,
        "raw_product_count": len(all_products),
    }


def should_write_output(result, output_file):
    products = result["products"]
    failed = result["failed"]

    if products:
        return True

    if failed and output_file.exists():
        return False

    if failed:
        return False

    return True


def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    shopify_retailers = [
        retailer
        for retailer in retailers
        if retailer.get("platform") == "shopify"
    ]

    print(f"Shopify retailers: {len(shopify_retailers)}")
    print("")

    total_products = 0
    skipped_outputs = 0

    for index, retailer in enumerate(shopify_retailers, start=1):
        print(f"[{index}/{len(shopify_retailers)}] {retailer['primary_name']}")

        output_file = OUTPUT_DIR / f"{safe_filename(retailer['primary_name'])}.json"

        result = scrape_shopify(retailer)
        products = result["products"]

        total_products += len(products)

        if not should_write_output(result, output_file):
            skipped_outputs += 1
            print(
                f"  Keeping existing output file because this scrape failed "
                f"or returned no usable products: {output_file}"
            )
            print("")
            continue

        output_file.write_text(
            json.dumps(products, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"  Saved: {output_file}")
        print("")

    print(f"Total extracted products this run: {total_products}")
    print(f"Outputs preserved due to failed or empty scrape: {skipped_outputs}")


if __name__ == "__main__":
    main()