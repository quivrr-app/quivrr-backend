from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.europe.normalise_eu_retailer_inventory import normalise_row


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
DEFAULT_MAX_PAGES = 0
TIMEOUT_SECONDS = 20
REGION_CODE = "EU"
HTML_WORKERS = 6

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
    "2 fin",
    "3 fin",
    "4 fin",
    "5 fin",
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
    variant_title = clean(variant.get("title"))
    product_title = clean(product.get("title"))
    if target.get("expandVariants") and variant_title.lower() not in {"", "default title"}:
        product_title = f"{product_title} - {variant_title}"
    source_snippet = " ".join(
        part for part in [
            clean(product.get("body_html")),
            variant_title,
            clean(variant.get("sku")),
        ] if part
    )

    return {
        "retailerSlug": target["retailerSlug"],
        "retailerName": target["retailerName"],
        "regionCode": target["regionCode"],
        "country": clean(target.get("country")),
        "platform": "shopify",
        "sourceUrl": clean(target.get("collectionUrl")),
        "productTitle": product_title,
        "productId": clean(product.get("id")),
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
        "sku": clean(variant.get("sku")),
        "sourceSnippet": source_snippet,
        "suspectedSurfboard": score["suspectedSurfboard"],
        "parseConfidence": score["parseConfidence"],
        "filterReasons": score["filterReasons"],
    }


class CollectionPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.product_handles: list[str] = []
        self.page_numbers: set[int] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        href = clean(values.get("href"))
        if tag == "a" and href:
            parsed = urlparse(href)
            page_values = parse_qs(parsed.query).get("page", [])
            for value in page_values:
                if value.isdigit():
                    self.page_numbers.add(int(value))

            match = re.search(r"/collections/[^/]+/products/([^/?#]+)", parsed.path)
            if match and match.group(1) not in self.product_handles:
                self.product_handles.append(match.group(1))


def html_page_url(collection_url: str, page: int) -> str:
    separator = "&" if "?" in collection_url else "?"
    return f"{collection_url}{separator}page={page}"


def fetch_collection_html_page(collection_url: str, page: int) -> dict:
    url = html_page_url(collection_url, page)
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS, headers=HEADERS)
        parser = CollectionPageParser()
        if response.status_code == 200:
            parser.feed(response.text)
        return {
            "page": page,
            "url": url,
            "ok": response.status_code == 200,
            "statusCode": response.status_code,
            "error": "",
            "handles": parser.product_handles,
            "pageNumbers": sorted(parser.page_numbers),
        }
    except Exception as error:
        return {
            "page": page,
            "url": url,
            "ok": False,
            "statusCode": None,
            "error": f"{type(error).__name__}: {error}",
            "handles": [],
            "pageNumbers": [],
        }


def crawl_visible_collection(target: dict) -> dict:
    collection_url = clean(target.get("collectionUrl"))
    first = fetch_collection_html_page(collection_url, 1)
    discovered_pages = max(first["pageNumbers"] or [1])
    expected_pages = int(target.get("visiblePages") or discovered_pages)
    total_pages = max(discovered_pages, expected_pages)
    pages = {1: first}

    with ThreadPoolExecutor(max_workers=HTML_WORKERS) as executor:
        futures = {
            executor.submit(fetch_collection_html_page, collection_url, page): page
            for page in range(2, total_pages + 1)
        }
        for future in as_completed(futures):
            result = future.result()
            pages[result["page"]] = result

    ordered = [pages[page] for page in sorted(pages)]
    failures = [page for page in ordered if not page["ok"]]
    occurrences = Counter(
        handle for page in ordered for handle in set(page.get("handles", []))
    )
    shared_handles = {
        handle for handle, count in occurrences.items() if count == len(ordered)
    }
    unique_handles = {
        handle
        for page in ordered
        for handle in page.get("handles", [])
        if handle not in shared_handles
    }
    return {
        "discoveredPages": discovered_pages,
        "expectedPages": expected_pages,
        "pagesCrawled": len(ordered),
        "firstPageUrl": ordered[0]["url"],
        "lastPageUrl": ordered[-1]["url"],
        "paginationMethod": "Shopify collection HTML ?page=N",
        "uniqueCollectionHandles": len(unique_handles),
        "sharedNonCollectionHandlesRemoved": sorted(shared_handles),
        "handles": sorted(unique_handles),
        "failures": failures,
        "pages": [
            {
                "page": page["page"],
                "url": page["url"],
                "statusCode": page["statusCode"],
                "productHandles": len(page["handles"]),
                "error": page["error"],
            }
            for page in ordered
        ],
    }


def canonical_product_key(product: dict) -> str:
    product_id = clean(product.get("id"))
    if product_id:
        return f"id:{product_id}"
    handle = clean(product.get("handle")).lower()
    if handle:
        return f"handle:{handle}"
    for variant in product.get("variants") or []:
        sku = clean(variant.get("sku")).lower()
        if sku:
            return f"sku:{sku}"
    return ""


def enrich_product(row: dict) -> tuple[dict, dict]:
    normalised = normalise_row(row)
    return {
        **row,
        "brand": normalised.get("brandName") or row.get("brand") or "",
        "model": normalised.get("modelName") or "",
        "lengthFeetInches": normalised.get("lengthFeetInches"),
        "volumeLitres": normalised.get("volumeLitres"),
    }, normalised


def discover_target(target: dict, max_pages: int) -> dict:
    if target.get("regionCode") != REGION_CODE:
        raise RuntimeError(
            f"EU Shopify discovery requires RegionCode 'EU', got {target.get('regionCode')!r}."
        )

    visible_collection = None
    if target.get("visiblePages"):
        visible_collection = crawl_visible_collection(target)

    accepted = []
    rejected_count = 0
    fetches = []
    raw_products = []
    page = 1

    while True:
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

        raw_products.extend(result["products"])

        if len(result["products"]) < PAGE_LIMIT:
            break
        if max_pages > 0 and page >= max_pages:
            break
        page += 1

    unique_products = {}
    for product in raw_products:
        key = canonical_product_key(product)
        if key and key not in unique_products:
            unique_products[key] = product

    normalised_rows = []
    for product in unique_products.values():
        variants = product.get("variants") or [{}]
        rows_to_parse = variants if target.get("expandVariants") else variants[:1]
        for variant in rows_to_parse:
            row = convert_product(product, variant, target)

            if row["suspectedSurfboard"]:
                enriched, normalised = enrich_product(row)
                accepted.append(enriched)
                normalised_rows.append(normalised)
            else:
                rejected_count += 1

    coverage_ok = True
    coverage_blocker = ""
    if visible_collection:
        api_handles = {
            clean(product.get("handle")) for product in unique_products.values()
        }
        visible_handles = set(visible_collection["handles"])
        missing_handles = sorted(visible_handles - api_handles)
        coverage_ok = all([
            not visible_collection["failures"],
            visible_collection["pagesCrawled"] >= visible_collection["expectedPages"],
            len(api_handles) >= visible_collection["uniqueCollectionHandles"],
            not missing_handles,
        ])
        if not coverage_ok:
            coverage_blocker = (
                f"html_pages={visible_collection['pagesCrawled']}/"
                f"{visible_collection['expectedPages']}, "
                f"html_unique={visible_collection['uniqueCollectionHandles']}, "
                f"api_unique={len(api_handles)}, missing_handles={len(missing_handles)}, "
                f"failed_pages={len(visible_collection['failures'])}"
            )
        visible_collection["apiMissingHandles"] = missing_handles[:100]

    diagnostics = {
        "pagesCrawled": visible_collection["pagesCrawled"] if visible_collection else len(fetches),
        "rawCategoryRows": len(raw_products),
        "uniqueCanonicalProducts": len(unique_products),
        "likelySurfboards": len(accepted),
        "normalisedRows": len(normalised_rows),
        "missingDimensions": sum(
            1
            for row in normalised_rows
            if not row.get("lengthFeetInches") and row.get("volumeLitres") is None
        ),
        "importableRows": sum(1 for row in normalised_rows if row.get("importableRaw")),
        "firstPageUrl": (
            visible_collection["firstPageUrl"] if visible_collection else fetches[0]["url"]
        ),
        "lastPageUrl": (
            visible_collection["lastPageUrl"] if visible_collection else fetches[-1]["url"]
        ),
        "paginationMethod": (
            "49-page Shopify collection HTML coverage check plus "
            "collection products.json limit=250&page=N to exhaustion"
            if visible_collection
            else "Shopify collection products.json limit=250&page=N to exhaustion"
        ),
        "coveragePassed": coverage_ok,
        "coverageBlocker": coverage_blocker,
    }

    return {
        "target": target["retailerSlug"],
        "diagnostics": diagnostics,
        "visibleCollection": visible_collection,
        "rawFetched": len(raw_products),
        "uniqueProducts": len(unique_products),
        "productsAccepted": len(accepted),
        "productsRejected": rejected_count,
        "fetches": fetches,
        "coveragePassed": coverage_ok,
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
        help="Optional Shopify JSON page cap. Default 0 fetches until exhausted.",
    )

    args = parser.parse_args()
    targets = load_targets()
    targets_to_run = selected_targets(targets, args.run_enabled, args.target)

    if not args.run_enabled:
        report = build_dry_run_report(targets)
    else:
        results = [
            discover_target(target, max(0, args.max_pages))
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
    for result in report.get("results", []):
        diagnostics = result.get("diagnostics", {})
        print(
            f"{result['target']}: pages={diagnostics.get('pagesCrawled', 0)} "
            f"raw={diagnostics.get('rawCategoryRows', 0)} "
            f"unique={diagnostics.get('uniqueCanonicalProducts', 0)} "
            f"likely={diagnostics.get('likelySurfboards', 0)} "
            f"normalised={diagnostics.get('normalisedRows', 0)} "
            f"missing_dimensions={diagnostics.get('missingDimensions', 0)} "
            f"importable={diagnostics.get('importableRows', 0)}"
        )
    print(f"Output: {OUTPUT_FILE}")
    failed = [
        result for result in report.get("results", [])
        if not result.get("coveragePassed", True)
    ]
    if failed:
        diagnostics = failed[0].get("diagnostics", {})
        raise RuntimeError(
            f"{failed[0]['target']} collection coverage failed: "
            f"first={diagnostics.get('firstPageUrl')}, "
            f"last={diagnostics.get('lastPageUrl')}, "
            f"pagination={diagnostics.get('paginationMethod')}, "
            f"blocker={diagnostics.get('coverageBlocker') or 'unknown'}"
        )


if __name__ == "__main__":
    main()
