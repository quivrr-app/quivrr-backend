import json
from pathlib import Path

import requests


OUTPUT_DIR = Path("scrapers/brands/channel_islands/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STORES = {
    "au": "https://shop-au.cisurfboards.com",
    "global": "https://cisurfboards.com",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)"
}

EXCLUDE_TERMS = [
    "gift",
    "card",
    "accessory",
    "accessories",
    "fin",
    "leash",
    "traction",
    "tailpad",
    "grip",
    "wax",
    "shirt",
    "tee",
    "hat",
    "sticker",
    "towel",
    "bag",
    "cover",
]


def looks_like_board(product: dict) -> bool:
    text = " ".join([
        str(product.get("title", "")),
        str(product.get("handle", "")),
        str(product.get("product_type", "")),
        " ".join(product.get("tags", [])),
    ]).lower()

    if any(term in text for term in EXCLUDE_TERMS):
        return False

    return (
        "surfboard" in text
        or "board" in text
        or product.get("product_type", "").lower() in ["surfboards", "surfboard"]
    )


def fetch_store_products(region: str, base_url: str) -> list:
    products = []
    page = 1

    while True:
        url = f"{base_url}/products.json?limit=250&page={page}"

        print(f"Fetching {region}: {url}")

        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        payload = response.json()
        page_products = payload.get("products", [])

        if not page_products:
            break

        for product in page_products:
            if not looks_like_board(product):
                continue

            images = product.get("images", [])

            products.append({
                "region": region,
                "store": base_url,
                "id": product.get("id"),
                "handle": product.get("handle"),
                "title": product.get("title"),
                "product_type": product.get("product_type"),
                "tags": product.get("tags", []),
                "vendor": product.get("vendor"),
                "product_url": f"{base_url}/products/{product.get('handle')}",
                "image_url": images[0].get("src") if images else None,
                "variant_count": len(product.get("variants", [])),
                "variants": [
                    {
                        "id": variant.get("id"),
                        "title": variant.get("title"),
                        "sku": variant.get("sku"),
                        "available": variant.get("available"),
                        "price": variant.get("price"),
                        "option1": variant.get("option1"),
                        "option2": variant.get("option2"),
                        "option3": variant.get("option3"),
                    }
                    for variant in product.get("variants", [])
                ],
            })

        page += 1

    return products


def main() -> None:
    all_products = []

    for region, base_url in STORES.items():
        try:
            all_products.extend(fetch_store_products(region, base_url))
        except Exception as exc:
            print(f"FAILED {region}: {exc}")

    output_path = OUTPUT_DIR / "ci_shopify_products_report.json"
    output_path.write_text(
        json.dumps(all_products, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("")
    print(f"Saved {len(all_products)} board products")
    print(output_path)

    print("")
    print("First 25:")
    for item in all_products[:25]:
        print(f"{item['region']} | {item['title']} | {item['handle']} | variants: {item['variant_count']}")


if __name__ == "__main__":
    main()
