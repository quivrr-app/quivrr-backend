from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scrapers.retailers.europe.common.discovery_utils import (  # noqa: E402
    clean,
    decorate_rows,
    product_rows_from_json_ld,
    product_rows_from_links,
)
from scrapers.retailers.europe.common.fetch_utils import fetch_text  # noqa: E402


INPUT_FILE = Path("scrapers/retailers/europe/magento/eu_magento_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/europe/magento/output/eu_magento_product_discovery.json")

LIVE_SEARCH_QUERY = """
query productSearch(
  $phrase: String!,
  $pageSize: Int,
  $currentPage: Int = 1,
  $filter: [SearchClauseInput!],
  $sort: [ProductSearchSortInput!],
  $context: QueryContextInput
) {
  productSearch(
    phrase: $phrase,
    page_size: $pageSize,
    current_page: $currentPage,
    filter: $filter,
    sort: $sort,
    context: $context
  ) {
    total_count
    items {
      product {
        sku
        name
        canonical_url
        image {
          url
          label
        }
        price_range {
          minimum_price {
            regular_price {
              value
              currency
            }
            final_price {
              value
              currency
            }
          }
        }
      }
    }
    page_info {
      current_page
      page_size
      total_pages
    }
  }
}
"""


def page_url(url: str, page: int) -> str:
    if page <= 1:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode({'p': page})}"


def absolute_url(url: object) -> str:
    text = clean(url)
    if text.startswith("//"):
        return f"https:{text}"
    return text


def price_from_live_search(product: dict) -> tuple[str, str]:
    price_range = product.get("price_range") if isinstance(product.get("price_range"), dict) else {}
    minimum = price_range.get("minimum_price") if isinstance(price_range.get("minimum_price"), dict) else {}
    final = minimum.get("final_price") if isinstance(minimum.get("final_price"), dict) else {}
    regular = minimum.get("regular_price") if isinstance(minimum.get("regular_price"), dict) else {}
    selected = final or regular
    value = selected.get("value")
    currency = clean(selected.get("currency") or "EUR")

    return (str(value) if value is not None else "", currency)


def live_search_category(target: dict, page: int) -> dict:
    config = target.get("liveSearch") or {}
    page_size = int(config.get("pageSize") or 36)
    customer_group = clean(config.get("customerGroup"))
    request_id = str(uuid.uuid4())
    variables = {
        "phrase": "",
        "pageSize": page_size,
        "currentPage": page,
        "filter": [
            {"attribute": "categoryPath", "eq": config.get("categoryPath", "surfboards")},
            {"attribute": "visibility", "in": ["Catalog", "Catalog, Search"]},
            {"attribute": "inStock", "eq": "true"},
        ],
        "sort": [{"attribute": "position", "direction": "ASC"}],
        "context": {"customerGroup": customer_group},
    }
    payload = json.dumps({"query": LIVE_SEARCH_QUERY, "variables": variables}).encode("utf-8")
    request = Request(
        clean(config.get("apiUrl")),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Magento-Environment-Id": clean(config.get("environmentId")),
            "Magento-Website-Code": clean(config.get("websiteCode")),
            "Magento-Store-Code": clean(config.get("storeCode")),
            "Magento-Store-View-Code": clean(config.get("storeViewCode")),
            "X-Api-Key": clean(config.get("apiKey")),
            "X-Request-Id": request_id,
            "Magento-Customer-Group": customer_group,
            "User-Agent": "Mozilla/5.0 QuivrrEUDiscovery/1.0",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            search = data.get("data", {}).get("productSearch", {})
            rows = []

            for item in search.get("items") or []:
                product = item.get("product") if isinstance(item, dict) else {}
                if not isinstance(product, dict):
                    continue

                price, currency = price_from_live_search(product)
                image = product.get("image") if isinstance(product.get("image"), dict) else {}
                rows.append({
                    "productTitle": clean(product.get("name")),
                    "productUrl": absolute_url(product.get("canonical_url")),
                    "productImageUrl": absolute_url(image.get("url")),
                    "brand": "",
                    "vendor": "",
                    "priceAmount": price,
                    "priceCurrency": currency,
                    "isAvailable": True,
                    "stockStatus": "in_stock",
                    "sku": clean(product.get("sku")),
                    "sourceSnippet": clean(product.get("name")),
                    "sourceUrl": target.get("categoryUrls", [""])[0],
                })

            return {
                "ok": True,
                "status": "ok",
                "httpStatus": getattr(response, "status", None),
                "url": clean(config.get("apiUrl")),
                "reason": "",
                "rows": rows,
                "totalCount": search.get("total_count"),
                "pageInfo": search.get("page_info", {}),
            }
    except HTTPError as error:
        return {
            "ok": False,
            "status": "http_error",
            "httpStatus": error.code,
            "url": clean(config.get("apiUrl")),
            "reason": f"HTTP {error.code}: {error.read(500).decode('utf-8', errors='replace')}",
            "rows": [],
        }
    except (URLError, TimeoutError, json.JSONDecodeError, Exception) as error:
        return {
            "ok": False,
            "status": "network_error",
            "httpStatus": None,
            "url": clean(config.get("apiUrl")),
            "reason": f"{type(error).__name__}: {error}",
            "rows": [],
        }


def discover_target(target: dict, max_pages: int) -> dict:
    products = []
    rejected = 0
    fetches = []

    if target.get("liveSearch"):
        for page in range(1, max_pages + 1):
            result = live_search_category(target, page)
            fetches.append({
                "url": result["url"],
                "status": result["status"],
                "httpStatus": result["httpStatus"],
                "finalUrl": result["url"],
                "reason": result["reason"],
                "source": "adobe_live_search",
                "totalCount": result.get("totalCount"),
                "pageInfo": result.get("pageInfo", {}),
            })

            if not result["ok"]:
                break

            accepted, rejected_count = decorate_rows(
                result["rows"],
                target,
                target.get("categoryUrls", [""])[0],
            )
            products.extend(accepted)
            rejected += rejected_count

            page_info = result.get("pageInfo") or {}
            total_pages = page_info.get("total_pages") or page
            if page >= total_pages:
                break

        return {
            "target": target["retailerSlug"],
            "productsAccepted": len(products),
            "productsRejected": rejected,
            "fetches": fetches,
            "products": products,
        }

    for category_url in target.get("categoryUrls", []):
        for page in range(1, max_pages + 1):
            source_url = page_url(category_url, page)
            response = fetch_text(source_url)
            fetches.append({
                "url": source_url,
                "status": response.status,
                "httpStatus": response.http_status,
                "finalUrl": response.final_url,
                "reason": response.reason,
            })

            if not response.ok:
                break

            rows = product_rows_from_json_ld(response.text, source_url)
            rows.extend(product_rows_from_links(response.text, source_url, [".html"]))
            accepted, rejected_count = decorate_rows(rows, target, source_url)
            products.extend(accepted)
            rejected += rejected_count

    return {
        "target": target["retailerSlug"],
        "productsAccepted": len(products),
        "productsRejected": rejected,
        "fetches": fetches,
        "products": products,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover EU Magento/html surfboard products without SQL writes.")
    parser.add_argument("--run-enabled", action="store_true", help="Fetch enabled targets. Without this, no network calls run.")
    parser.add_argument("--target", default="", help="Optional retailerSlug filter.")
    parser.add_argument("--max-pages", type=int, default=1, help="Maximum pages per category URL.")
    args = parser.parse_args()

    targets = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    selected = [target for target in targets if args.run_enabled and target.get("enabled") is True]
    if args.target:
        selected = [target for target in selected if target.get("retailerSlug") == args.target]

    results = [discover_target(target, max(1, args.max_pages)) for target in selected]
    products = [product for result in results for product in result["products"]]
    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "run_enabled" if args.run_enabled else "dry_run",
        "purpose": "EU Magento/html product discovery only. No SQL import or production table writes.",
        "targetsConfigured": len(targets),
        "targetsSelected": len(selected),
        "results": [{key: value for key, value in result.items() if key != "products"} for result in results],
        "products": products,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"EU Magento/html discovery: {report['mode']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
