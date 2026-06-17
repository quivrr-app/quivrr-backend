from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
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
from scrapers.retailers.europe.normalise_eu_retailer_inventory import (  # noqa: E402
    normalise_row,
)


INPUT_FILE = Path("scrapers/retailers/europe/magento/eu_magento_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/europe/magento/output/eu_magento_product_discovery.json")
REGION_CODE = "EU"
SHORTBOARD_BENCHMARK = 929
SHORTBOARD_MINIMUM = 790

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


def live_search_category(
    target: dict,
    page: int,
    category_path: str | None = None,
    source_url: str | None = None,
) -> dict:
    config = target.get("liveSearch") or {}
    page_size = int(config.get("pageSize") or 36)
    customer_group = clean(config.get("customerGroup"))
    request_id = str(uuid.uuid4())
    variables = {
        "phrase": "",
        "pageSize": page_size,
        "currentPage": page,
        "filter": [
            {
                "attribute": "categoryPath",
                "eq": category_path or config.get("categoryPath", "surfboards"),
            },
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
                    "productId": clean(product.get("sku")),
                    "sourceSnippet": clean(product.get("name")),
                    "sourceUrl": source_url or target.get("categoryUrls", [""])[0],
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


class SurfboardNavigationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.routes: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        parsed = urlsplit(href)
        if parsed.netloc and parsed.netloc not in {"58surf.com", "www.58surf.com"}:
            return
        if parsed.path.rstrip("/").startswith("/eng/surfboards"):
            route = urlunsplit(("https", "58surf.com", parsed.path.rstrip("/"), "", ""))
            if route not in self.routes:
                self.routes.append(route)


def discover_category_routes(target: dict) -> dict:
    start_url = clean(
        target.get("startingCategoryUrl")
        or target.get("categoryUrls", ["https://58surf.com/eng/surfboards/shortboards"])[0]
    )
    response = fetch_text(start_url)
    routes = []
    if response.ok:
        parser = SurfboardNavigationParser()
        parser.feed(response.text)
        routes = parser.routes

    configured = [*target.get("categoryUrls", []), *target.get("relatedCategoryUrls", [])]
    for route in configured:
        canonical = route.rstrip("/")
        if canonical and canonical not in routes:
            routes.append(canonical)

    shortboard_url = "https://58surf.com/eng/surfboards/shortboards"
    routes = sorted(
        set(routes),
        key=lambda route: (route != shortboard_url, route.count("/"), route),
    )
    return {
        "startUrl": start_url,
        "status": response.status,
        "httpStatus": response.http_status,
        "reason": response.reason,
        "routes": routes,
    }


def category_path_from_url(url: str) -> str:
    path = urlsplit(url).path.strip("/")
    return path[4:] if path.startswith("eng/") else path


def canonical_product_key(row: dict) -> str:
    product_url = clean(row.get("productUrl"))
    if product_url:
        parsed = urlsplit(product_url)
        return urlunsplit(
            (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", "")
        ).lower()
    return clean(row.get("productId") or row.get("sku")).lower()


def enrich_product(row: dict) -> tuple[dict, dict]:
    normalised = normalise_row(row)
    enriched = {
        **row,
        "productId": clean(row.get("productId") or row.get("sku")),
        "brand": normalised.get("brandName") or row.get("brand") or "",
        "model": normalised.get("modelName") or "",
        "lengthFeetInches": normalised.get("lengthFeetInches"),
        "volumeLitres": normalised.get("volumeLitres"),
    }
    return enriched, normalised


def discover_target(target: dict, max_pages: int) -> dict:
    if target.get("regionCode") != REGION_CODE:
        raise RuntimeError(
            f"58 Surf discovery requires RegionCode 'EU', got {target.get('regionCode')!r}."
        )

    products = []
    rejected = 0
    fetches = []

    if target.get("liveSearch"):
        navigation = discover_category_routes(target)
        raw_rows = []
        category_diagnostics = []

        for route in navigation["routes"]:
            category_path = category_path_from_url(route)
            page = 1
            category_rows = 0
            total_count = None
            total_pages = None
            blocker = ""

            while True:
                result = live_search_category(target, page, category_path, route)
                fetches.append({
                    "endpoint": result["url"],
                    "categoryUrl": route,
                    "categoryPath": category_path,
                    "pagination": {
                        "method": "GraphQL current_page/page_size",
                        "currentPage": page,
                    },
                    "status": result["status"],
                    "httpStatus": result["httpStatus"],
                    "reason": result["reason"],
                    "source": "adobe_live_search",
                    "rowsFetched": len(result.get("rows", [])),
                    "totalCount": result.get("totalCount"),
                    "pageInfo": result.get("pageInfo", {}),
                })
                if not result["ok"]:
                    blocker = result["reason"] or result["status"]
                    break

                rows = result.get("rows", [])
                raw_rows.extend(rows)
                category_rows += len(rows)
                page_info = result.get("pageInfo") or {}
                total_count = result.get("totalCount")
                total_pages = int(page_info.get("total_pages") or page)
                if not rows or page >= total_pages:
                    break
                if max_pages > 0 and page >= max_pages:
                    blocker = f"page cap reached at {max_pages} of {total_pages}"
                    break
                page += 1

            category_diagnostics.append({
                "categoryUrl": route,
                "categoryPath": category_path,
                "apiEndpoint": clean((target.get("liveSearch") or {}).get("apiUrl")),
                "paginationMethod": "GraphQL current_page/page_size",
                "pageSize": int((target.get("liveSearch") or {}).get("pageSize") or 36),
                "pagesFetched": page,
                "reportedTotal": total_count,
                "rawFetched": category_rows,
                "exhausted": not blocker and (total_pages is None or page >= total_pages),
                "blocker": blocker,
            })

        unique_rows = {}
        for row in raw_rows:
            key = canonical_product_key(row)
            if key and key not in unique_rows:
                unique_rows[key] = row

        accepted, rejected = decorate_rows(
            list(unique_rows.values()), target, navigation["startUrl"]
        )
        normalised_rows = []
        for row in accepted:
            enriched, normalised = enrich_product(row)
            products.append(enriched)
            normalised_rows.append(normalised)

        shortboards = next(
            (
                item
                for item in category_diagnostics
                if item["categoryPath"] == "surfboards/shortboards"
            ),
            None,
        )
        benchmark_ok = bool(
            shortboards
            and shortboards["rawFetched"] >= SHORTBOARD_MINIMUM
            and shortboards["exhausted"]
        )
        diagnostics = {
            "rawFetched": len(raw_rows),
            "uniqueProducts": len(unique_rows),
            "likelySurfboards": len(products),
            "normalisedRows": len(normalised_rows),
            "missingDimensions": sum(
                1
                for row in normalised_rows
                if not row.get("lengthFeetInches") and row.get("volumeLitres") is None
            ),
            "importableRows": sum(
                1 for row in normalised_rows if row.get("importableRaw")
            ),
            "shortboardBenchmark": {
                "expected": SHORTBOARD_BENCHMARK,
                "minimum": SHORTBOARD_MINIMUM,
                "actual": shortboards["rawFetched"] if shortboards else 0,
                "passed": benchmark_ok,
            },
        }

        return {
            "target": target["retailerSlug"],
            "navigation": navigation,
            "categoryDiagnostics": category_diagnostics,
            "diagnostics": diagnostics,
            "rawFetched": len(raw_rows),
            "uniqueProducts": len(unique_rows),
            "productsAccepted": len(products),
            "productsRejected": rejected,
            "fetches": fetches,
            "benchmarkPassed": benchmark_ok,
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
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Optional safety page cap per category. Default 0 fetches until exhausted.",
    )
    args = parser.parse_args()

    targets = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    selected = [target for target in targets if args.run_enabled and target.get("enabled") is True]
    if args.target:
        selected = [target for target in selected if target.get("retailerSlug") == args.target]

    results = [discover_target(target, max(0, args.max_pages)) for target in selected]
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
    for result in results:
        diagnostics = result.get("diagnostics", {})
        print(
            f"{result['target']}: raw={diagnostics.get('rawFetched', 0)} "
            f"unique={diagnostics.get('uniqueProducts', 0)} "
            f"likely={diagnostics.get('likelySurfboards', 0)} "
            f"normalised={diagnostics.get('normalisedRows', 0)} "
            f"missing_dimensions={diagnostics.get('missingDimensions', 0)} "
            f"importable={diagnostics.get('importableRows', 0)}"
        )
    print(f"Output: {OUTPUT_FILE}")
    failed = [result for result in results if not result.get("benchmarkPassed", True)]
    if failed:
        shortboard = next(
            (
                item
                for item in failed[0].get("categoryDiagnostics", [])
                if item.get("categoryPath") == "surfboards/shortboards"
            ),
            {},
        )
        raise RuntimeError(
            "58 Surf shortboard discovery below benchmark: "
            f"endpoint={shortboard.get('apiEndpoint')}, "
            f"pagination={shortboard.get('paginationMethod')}, "
            f"raw={shortboard.get('rawFetched', 0)}, "
            f"blocker={shortboard.get('blocker') or 'unknown'}"
        )


if __name__ == "__main__":
    main()
