from pathlib import Path
import json
import requests
from requests.exceptions import SSLError
from requests.exceptions import ConnectionError
from requests.exceptions import Timeout


INPUT_FILES = [
    Path("scrapers/retailers/retailer_scrape_targets_classified.json"),
    Path("scrapers/retailers/retailer_expansion_candidates_au.json"),
]

OUTPUT_FILE = Path(
    "scrapers/retailers/retailer_platform_detection_report.json"
)

TIMEOUT_SECONDS = 20


SUPPORTED_PLATFORMS = {
    "shopify",
    "woocommerce",
    "bigcommerce",
    "neto_maropost",
    "wix",
    "squarespace",
    "ecwid",
    "magento",
    "opencart",
    "shopline",
    "lightspeed",
    "square_online",
}


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def normalise_url(url):
    url = clean(url)

    if not url:
        return ""

    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    return url.rstrip("/")


def fetch(url, verify=True):
    try:
        response = requests.get(
            url,
            timeout=TIMEOUT_SECONDS,
            allow_redirects=True,
            verify=verify,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/137.0 Safari/537.36 "
                    "QuivrrRetailCrawler/1.0"
                )
            },
        )

        return response

    except SSLError as error:
        return {
            "exception_type": "ssl_error",
            "message": str(error),
        }

    except Timeout as error:
        return {
            "exception_type": "timeout",
            "message": str(error),
        }

    except ConnectionError as error:
        return {
            "exception_type": "connection_error",
            "message": str(error),
        }

    except Exception as error:
        return {
            "exception_type": "generic_error",
            "message": str(error),
        }


def response_text(response):
    try:
        return response.text.lower()

    except Exception:
        return ""


def is_response(response):
    return hasattr(response, "status_code")


def detect_shopify(website):
    url = f"{website}/products.json?limit=1"

    response = fetch(url)

    if not is_response(response):
        return None

    if response.status_code == 200:
        try:
            data = response.json()

            if isinstance(data, dict) and "products" in data:
                return {
                    "platform": "shopify",
                    "status": "supported",
                    "evidence": url,
                }

        except Exception:
            pass

    return None


def detect_woocommerce(website):
    urls = [
        f"{website}/wp-json/wc/store/products?per_page=1",
        f"{website}/wp-json/wc/v3/products",
    ]

    for url in urls:
        response = fetch(url)

        if not is_response(response):
            continue

        if response.status_code == 200:
            return {
                "platform": "woocommerce",
                "status": "supported",
                "evidence": url,
            }

    return None


def detect_bigcommerce(text):
    markers = [
        "cdn11.bigcommerce.com",
        "bigcommerce",
        "stencil-utils",
    ]

    return any(marker in text for marker in markers)


def detect_neto(text):
    markers = [
        "maropost",
        "neto",
        "/assets/neto/",
    ]

    return any(marker in text for marker in markers)


def detect_wix(text):
    markers = [
        "wix.com",
        "_wixcssrules",
        "static.wixstatic.com",
        "wix-image",
    ]

    return any(marker in text for marker in markers)


def detect_squarespace(text):
    markers = [
        "static.squarespace.com",
        "squarespace",
        "sqs-block",
    ]

    return any(marker in text for marker in markers)


def detect_ecwid(text):
    markers = [
        "ecwid",
        "ec.store",
        "storefront.ecwid.com",
    ]

    return any(marker in text for marker in markers)


def detect_magento(text):
    markers = [
        "mage/",
        "magento",
        "Magento_Ui",
    ]

    return any(marker in text for marker in markers)


def detect_opencart(text):
    markers = [
        "index.php?route=",
        "opencart",
    ]

    return any(marker in text for marker in markers)


def detect_shopline(text):
    markers = [
        "shopline",
        "myshopline",
    ]

    return any(marker in text for marker in markers)


def detect_lightspeed(text):
    markers = [
        "lightspeed",
        "ecwid-lightspeed",
    ]

    return any(marker in text for marker in markers)


def detect_square_online(text):
    markers = [
        "square.site",
        "squareup",
        "square-online",
    ]

    return any(marker in text for marker in markers)


def detect_algolia(text):
    markers = [
        "algolia",
        "algolianet",
    ]

    return any(marker in text for marker in markers)


def detect_generic_catalogue(text):
    product_markers = [
        "/products/",
        "/product/",
        "add to cart",
        "out of stock",
        "buy now",
        "surfboard",
    ]

    score = 0

    for marker in product_markers:
        if marker in text:
            score += 1

    return score >= 2


def classify_homepage(website):
    response = fetch(website)

    if isinstance(response, dict):
        exception_type = response.get("exception_type")

        if exception_type == "ssl_error":
            retry = fetch(website, verify=False)

            if is_response(retry):
                return {
                    "platform": "ssl_problem_site",
                    "status": "needs_review",
                    "evidence": "SSL verification failed but site loaded with verify=False",
                }

        return {
            "platform": exception_type or "error",
            "status": "failed",
            "evidence": response.get("message"),
        }

    status_code = response.status_code

    if status_code in {401, 403, 429}:
        return {
            "platform": "blocked",
            "status": "blocked",
            "evidence": f"Homepage returned {status_code}",
        }

    text = response_text(response)

    if detect_bigcommerce(text):
        return {
            "platform": "bigcommerce",
            "status": "needs_adapter",
            "evidence": "Detected BigCommerce markers",
        }

    if detect_neto(text):
        return {
            "platform": "neto_maropost",
            "status": "needs_adapter",
            "evidence": "Detected Neto/Maropost markers",
        }

    if detect_wix(text):
        return {
            "platform": "wix",
            "status": "needs_adapter",
            "evidence": "Detected Wix markers",
        }

    if detect_squarespace(text):
        return {
            "platform": "squarespace",
            "status": "needs_adapter",
            "evidence": "Detected Squarespace markers",
        }

    if detect_ecwid(text):
        return {
            "platform": "ecwid",
            "status": "needs_adapter",
            "evidence": "Detected Ecwid markers",
        }

    if detect_magento(text):
        return {
            "platform": "magento",
            "status": "needs_adapter",
            "evidence": "Detected Magento markers",
        }

    if detect_opencart(text):
        return {
            "platform": "opencart",
            "status": "needs_adapter",
            "evidence": "Detected OpenCart markers",
        }

    if detect_shopline(text):
        return {
            "platform": "shopline",
            "status": "needs_adapter",
            "evidence": "Detected Shopline markers",
        }

    if detect_lightspeed(text):
        return {
            "platform": "lightspeed",
            "status": "needs_adapter",
            "evidence": "Detected Lightspeed markers",
        }

    if detect_square_online(text):
        return {
            "platform": "square_online",
            "status": "needs_adapter",
            "evidence": "Detected Square Online markers",
        }

    if detect_algolia(text):
        return {
            "platform": "algolia",
            "status": "needs_adapter",
            "evidence": "Detected Algolia markers",
        }

    if detect_generic_catalogue(text):
        return {
            "platform": "generic_catalogue",
            "status": "needs_generic_scraper",
            "evidence": "Detected generic product catalogue structure",
        }

    return {
        "platform": "unknown",
        "status": "needs_review",
        "evidence": f"Homepage returned {status_code}",
    }


def detect_platform(website):
    website = normalise_url(website)

    if not website:
        return {
            "platform": "missing_website",
            "status": "failed",
            "evidence": "No website provided",
        }

    shopify = detect_shopify(website)

    if shopify:
        return shopify

    woocommerce = detect_woocommerce(website)

    if woocommerce:
        return woocommerce

    return classify_homepage(website)


def retailer_name(record):
    return (
        clean(record.get("primary_name"))
        or clean(record.get("name"))
        or clean(record.get("retailer_name"))
        or clean(record.get("website"))
    )


def load_records():
    records = []

    for path in INPUT_FILES:
        if not path.exists():
            continue

        data = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            records.extend(data)

    return records


def main():
    records = load_records()

    results = []
    seen = set()

    print("")
    print("Quivrr retailer platform detection")
    print("=" * 60)
    print(f"Retailer records loaded: {len(records)}")

    for index, record in enumerate(records, start=1):
        website = normalise_url(record.get("website"))

        if not website:
            continue

        website_key = website.lower().replace("www.", "")

        if website_key in seen:
            continue

        seen.add(website_key)

        name = retailer_name(record)

        print(f"[{index}/{len(records)}] {name}")

        detected = detect_platform(website)

        results.append({
            "primary_name": name,
            "website": website,
            "detected_platform": detected["platform"],
            "status": detected["status"],
            "evidence": detected["evidence"],
            "existing_platform": clean(
                record.get("platform")
                or record.get("ecommerce_platform")
            ),
            "manufacturer_or_brand": bool(
                record.get("manufacturer_or_brand")
            ),
            "hardboards": record.get("hardboards"),
            "priority": record.get("priority", 3),
        })

    summary = {}

    for result in results:
        key = f"{result['status']}:{result['detected_platform']}"
        summary[key] = summary.get(key, 0) + 1

    report = {
        "total_input_records": len(records),
        "unique_websites_checked": len(results),
        "summary": summary,
        "results": results,
    }

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("")
    print("Platform detection complete")
    print("=" * 60)

    for key, value in sorted(summary.items()):
        print(f"{key}: {value}")

    print("")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()