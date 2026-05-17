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


def fetch_shopify_products_from_url(url):
    try:
        response = requests.get(
            url,
            timeout=30,
            headers=HEADERS,
        )

        if response.status_code != 200:
            return {
                "products": [],
                "failed": True,
                "status_code": response.status_code,
                "error": None,
            }

        data = response.json()

        return {
            "products": data.get("products", []),
            "failed": False,
            "status_code": response.status_code,
            "error": None,
        }

    except Exception as exc:
        return {
            "products": [],
            "failed": True,
            "status_code": None,
            "error": str(exc),
        }


def scrape_shopify_endpoint(base, page):
    url = f"{base}/products.json?limit={PAGE_LIMIT}&page={page}"
    return fetch_shopify_products_from_url(url)


def scrape_shopify_collection(base, handle, page):
    url = (
        f"{base}/collections/{handle}/products.json"
        f"?limit={PAGE_LIMIT}&page={page}"
    )
    return fetch_shopify_products_from_url(url)


def dedupe_products(products):
    seen = set()
    deduped = []

    for product in products:
        product_id = product.get("id")
        handle = product.get("handle")
        key = product_id or handle

        if not key:
            deduped.append(product)
            continue

        if key in seen:
            continue

        seen.add(key)
        deduped.append(product)

    return deduped


def scrape_standard_shopify(retailer):
    base = retailer["website"].rstrip("/")
    page = 1
    all_products = []
    failed = False

    while page <= MAX_PAGES:
        result = scrape_shopify_endpoint(base, page)

        if result["failed"]:
            print(
                f"  FAILED page {page}: "
                f"{result.get('status_code') or result.get('error')}"
            )
            failed = True
            break

        products = result["products"]

        if not products:
            break

        print(f"  Page {page}: {len(products)} products")
        all_products.extend(products)

        if len(products) < PAGE_LIMIT:
            break

        page += 1

    return {
        "products": all_products,
        "failed": failed,
    }


def scrape_collection_shopify(retailer):
    base = retailer["website"].rstrip("/")
    handles = retailer.get("collection_handles") or []
    all_products = []
    failed = False

    for handle in handles:
        page = 1

        print(f"  Collection: {handle}")

        while page <= MAX_PAGES:
            result = scrape_shopify_collection(base, handle, page)

            if result["failed"]:
                print(
                    f"    FAILED page {page}: "
                    f"{result.get('status_code') or result.get('error')}"
                )
                failed = True
                break

            products = result["products"]

            if not products:
                break

            print(f"    Page {page}: {len(products)} products")
            all_products.extend(products)

            if len(products) < PAGE_LIMIT:
                break

            page += 1

    all_products = dedupe_products(all_products)

    return {
        "products": all_products,
        "failed": failed,
    }


def scrape_shopify(retailer):
    print(f"Scraping: {retailer['primary_name']}")

    if retailer.get("collection_handles"):
        result = scrape_collection_shopify(retailer)
    else:
        result = scrape_standard_shopify(retailer)

    all_products = result["products"]

    print(f"  Total products: {len(all_products)}")

    extracted = extract_products(all_products, retailer)

    return {
        "products": extracted,
        "failed": result["failed"],
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