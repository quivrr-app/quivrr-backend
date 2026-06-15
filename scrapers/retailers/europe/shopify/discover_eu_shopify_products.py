from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests


INPUT_FILE = Path("scrapers/retailers/europe/shopify/eu_shopify_targets.json")
OUTPUT_FILE = Path(
    "scrapers/retailers/europe/shopify/output/eu_shopify_product_discovery.json"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36 QuivrrEUShopifyDiscovery/1.0"
    ),
    "Accept": "application/json,text/html,*/*",
}

PAGE_LIMIT = 250
DEFAULT_MAX_PAGES = 2
TIMEOUT_SECONDS = 20

BOARD_TERMS = [
    "surfboard",
    "surfboards",
    "surf board",
    "shortboard",
    "longboard",
    "mid length",
    "midlength",
    "mid-length",
    "fish",
    "twin fin",
    "gun",
    "funboard",
    "mini mal",
    "malibu",
    "foamie",
    "softboard",
    "performance board",
]

BOARD_BRANDS = [
    "album",
    "aloha",
    "channel islands",
    "christenson",
    "chilli",
    "ci surfboards",
    "dhd",
    "firewire",
    "haydenshapes",
    "js industries",
    "lost",
    "mayhem",
    "misfit",
    "modern",
    "mctavish",
    "nsp",
    "pukas",
    "pyzel",
    "rusty",
    "sharp eye",
    "sharpeye",
    "slater designs",
    "torq",
]

EXCLUDE_TERMS = [
    "accessories",
    "accessory",
    "beanie",
    "bikini",
    "bodyboard",
    "board bag",
    "board sock",
    "boardshort",
    "cap",
    "clothing",
    "deck grip",
    "dress",
    "fins",
    "fin set",
    "gift card",
    "grip pad",
    "hat",
    "jacket",
    "leash",
    "leg rope",
    "legrope",
    "pants",
    "poncho",
    "rash vest",
    "shirt",
    "shorts",
    "skateboard",
    "snowboard",
    "soft rack",
    "soft racks",
    "sunscreen",
    "tail pad",
    "tee",
    "traction",
    "travel bag",
    "t-shirt",
    "voucher",
    "wax",
    "wetsuit",
]

DIMENSION_PATTERN = re.compile(
    r"\b(?:[4-9]|1[0-2])\s*(?:'|ft|’)\s*\d{0,2}\b",
    re.IGNORECASE,
)

LITRE_PATTERN = re.compile(
    r"\b(?:1[5-9]|[2-7]\d|8[0-5])(?:\.\d{1,2})?\s*(?:l|ltr|litre|litres)\b",
    re.IGNORECASE,
)


def clean(value: object) -> str:
    if value is None:
        return ""

    return str(value).strip()


def lower_text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(lower_text(item) for item in value)

    if isinstance(value, dict):
        return " ".join(lower_text(item) for item in value.values())

    return clean(value).lower()


def contains_phrase(text: str, phrases: list[str]) -> bool:
    for phrase in phrases:
        pattern = rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])"

        if re.search(pattern, text):
            return True

    return False


def normalise_base_url(url: str) -> str:
    parsed = urlparse(clean(url))

    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def collection_products_url(target: dict, page: int) -> str:
    collection_url = clean(target.get("collectionUrl"))

    if not collection_url:
        base = normalise_base_url(target["website"])
        return f"{base}/products.json?limit={PAGE_LIMIT}&page={page}"

    parsed = urlparse(collection_url)
    base = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    path = parsed.path.rstrip("/")

    if not path:
        return f"{base}/products.json?limit={PAGE_LIMIT}&page={page}"

    if path.endswith("/products.json"):
        return f"{base}{path}?limit={PAGE_LIMIT}&page={page}"

    return f"{base}{path}/products.json?limit={PAGE_LIMIT}&page={page}"


def product_url(target: dict, handle: str) -> str:
    base = normalise_base_url(target["website"])

    if not handle:
        return base

    return f"{base}/products/{handle}"


def fetch_products(url: str) -> dict:
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS, headers=HEADERS)

        if response.status_code != 200:
            return {
                "ok": False,
                "statusCode": response.status_code,
                "error": "",
                "products": [],
            }

        data = response.json()

        return {
            "ok": True,
            "statusCode": response.status_code,
            "error": "",
            "products": data.get("products", []),
        }
    except Exception as error:
        return {
            "ok": False,
            "statusCode": None,
            "error": f"{type(error).__name__}: {error}",
            "products": [],
        }


def product_text(product: dict, variant: dict) -> str:
    parts = [
        product.get("title"),
        product.get("handle"),
        product.get("vendor"),
        product.get("product_type"),
        product.get("tags"),
        variant.get("title"),
        variant.get("sku"),
    ]

    return " ".join(lower_text(part) for part in parts if part)


def parse_price(value: object) -> float | None:
    text = clean(value).replace(",", "")

    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def score_product(product: dict, variant: dict) -> dict:
    text = product_text(product, variant)
    price = parse_price(variant.get("price"))
    reasons = []
    confidence = 0

    if not text:
        return {
            "suspectedSurfboard": False,
            "parseConfidence": 0,
            "filterReasons": ["missing_text"],
        }

    if contains_phrase(text, EXCLUDE_TERMS):
        return {
            "suspectedSurfboard": False,
            "parseConfidence": 0,
            "filterReasons": ["excluded_product_type"],
        }

    if price is not None and price < 250:
        return {
            "suspectedSurfboard": False,
            "parseConfidence": 0,
            "filterReasons": ["price_too_low"],
        }

    if contains_phrase(text, BOARD_TERMS):
        confidence += 4
        reasons.append("board_term")

    if contains_phrase(text, BOARD_BRANDS):
        confidence += 3
        reasons.append("known_board_brand")

    if DIMENSION_PATTERN.search(text):
        confidence += 3
        reasons.append("length_signal")

    if LITRE_PATTERN.search(text):
        confidence += 3
        reasons.append("volume_signal")

    if price is not None and price >= 400:
        confidence += 1
        reasons.append("realistic_board_price")

    suspected = confidence >= 5 and (
        "board_term" in reasons
        or "length_signal" in reasons
        or "volume_signal" in reasons
    )

    if not suspected:
        reasons.append("low_confidence_or_missing_board_identity")

    return {
        "suspectedSurfboard": suspected,
        "parseConfidence": confidence,
        "filterReasons": reasons,
    }


def first_image(product: dict) -> str:
    images = product.get("images") or []

    for image in images:
        if isinstance(image, dict) and image.get("src"):
            return image["src"]

    image = product.get("image")

    if isinstance(image, dict):
        return clean(image.get("src"))

    return ""


def option_names(product: dict) -> list[str]:
    options = product.get("options") or []
    names = []

    for option in options:
        if isinstance(option, dict) and option.get("name"):
            names.append(clean(option["name"]))

    return names


def variant_titles(product: dict) -> list[str]:
    titles = []

    for variant in product.get("variants") or []:
        title = clean(variant.get("title"))

        if title and title not in titles:
            titles.append(title)

    return titles


def convert_product(product: dict, variant: dict, target: dict) -> dict:
    score = score_product(product, variant)
    handle = clean(product.get("handle"))

    return {
        "retailerSlug": target["retailerSlug"],
        "retailerName": target["retailerName"],
        "regionCode": target["regionCode"],
        "productTitle": clean(product.get("title")),
        "productUrl": product_url(target, handle),
        "productImageUrl": first_image(product),
        "vendor": clean(product.get("vendor")),
        "brand": clean(product.get("vendor")),
        "priceAmount": clean(variant.get("price")),
        "priceCurrency": target.get("priceCurrency", "EUR"),
        "availability": variant.get("available"),
        "optionNames": option_names(product),
        "variantTitles": variant_titles(product),
        "rawHandle": handle,
        "suspectedSurfboard": score["suspectedSurfboard"],
        "parseConfidence": score["parseConfidence"],
        "filterReasons": score["filterReasons"],
    }


def discover_target(target: dict, max_pages: int) -> dict:
    accepted = []
    rejected_count = 0
    fetches = []

    for page in range(1, max_pages + 1):
        url = collection_products_url(target, page)
        result = fetch_products(url)

        fetches.append({
            "url": url,
            "ok": result["ok"],
            "statusCode": result["statusCode"],
            "error": result["error"],
            "productCount": len(result["products"]),
        })

        if not result["ok"] or not result["products"]:
            break

        for product in result["products"]:
            variants = product.get("variants") or [{}]
            primary_variant = variants[0] if variants else {}
            row = convert_product(product, primary_variant, target)

            if row["suspectedSurfboard"]:
                accepted.append(row)
            else:
                rejected_count += 1

        if len(result["products"]) < PAGE_LIMIT:
            break

    return {
        "target": target["retailerSlug"],
        "productsAccepted": len(accepted),
        "productsRejected": rejected_count,
        "fetches": fetches,
        "products": accepted,
    }


def load_targets() -> list[dict]:
    return json.loads(INPUT_FILE.read_text(encoding="utf-8"))


def selected_targets(targets: list[dict], run_enabled: bool, target_slug: str) -> list[dict]:
    selected = targets

    if target_slug:
        selected = [
            target
            for target in selected
            if target.get("retailerSlug") == target_slug
        ]

    if run_enabled:
        selected = [
            target
            for target in selected
            if target.get("enabled") is True
        ]
    else:
        selected = []

    return selected


def build_dry_run_report(targets: list[dict]) -> dict:
    return {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run",
        "purpose": "EU Shopify product discovery scaffold. No network fetches, SQL writes, imports, or production file writes.",
        "targetsConfigured": len(targets),
        "targetsEnabled": len([target for target in targets if target.get("enabled") is True]),
        "outputFile": str(OUTPUT_FILE),
        "targets": [
            {
                "retailerSlug": target["retailerSlug"],
                "retailerName": target["retailerName"],
                "regionCode": target["regionCode"],
                "enabled": target["enabled"],
                "collectionUrl": target["collectionUrl"],
            }
            for target in targets
        ],
        "products": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover likely EU Shopify surfboard products without importing to SQL."
    )
    parser.add_argument(
        "--run-enabled",
        action="store_true",
        help="Fetch products for targets where enabled is true. Without this flag, no network product discovery runs.",
    )
    parser.add_argument(
        "--target",
        default="",
        help="Optional retailerSlug filter. The target must still be enabled when --run-enabled is used.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Maximum Shopify products.json pages per enabled target.",
    )

    args = parser.parse_args()
    targets = load_targets()
    targets_to_run = selected_targets(targets, args.run_enabled, args.target)

    if not args.run_enabled:
        report = build_dry_run_report(targets)
    else:
        results = [
            discover_target(target, max(1, args.max_pages))
            for target in targets_to_run
        ]
        products = [
            product
            for result in results
            for product in result["products"]
        ]

        report = {
            "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
            "mode": "run_enabled",
            "purpose": "EU Shopify product discovery only. No SQL import and no production table writes.",
            "regionCode": "EU",
            "priceCurrencyDefault": "EUR",
            "targetsConfigured": len(targets),
            "targetsSelected": len(targets_to_run),
            "results": [
                {
                    key: value
                    for key, value in result.items()
                    if key != "products"
                }
                for result in results
            ],
            "products": products,
        }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("EU Shopify product discovery")
    print(f"Mode: {report['mode']}")
    print(f"Targets configured: {report['targetsConfigured']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
