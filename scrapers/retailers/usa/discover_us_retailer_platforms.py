from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


INPUT_FILE = Path("scrapers/retailers/usa/us_retailer_targets.json")
OUTPUT_FILE = Path("scrapers/retailers/usa/output/us_retailer_discovery.json")
TIMEOUT_SECONDS = 12
MAX_BYTES = 350_000


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0 Safari/537.36 QuivrrUSDiscovery/1.0"
)


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_url(value: object) -> str:
    url = clean(value)
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    if not parsed.netloc:
        return ""
    return url.rstrip("/")


def fetch_text(url: str) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_BYTES)
            encoding = response.headers.get_content_charset() or "utf-8"
            return {
                "ok": True,
                "statusCode": getattr(response, "status", None),
                "finalUrl": response.geturl(),
                "text": body.decode(encoding, errors="replace").lower(),
            }
    except HTTPError as error:
        return {
            "ok": False,
            "statusCode": error.code,
            "finalUrl": url,
            "error": f"http_error:{error.code}",
            "text": "",
        }
    except URLError as error:
        return {
            "ok": False,
            "statusCode": None,
            "finalUrl": url,
            "error": f"url_error:{error.reason}",
            "text": "",
        }
    except Exception as error:
        return {
            "ok": False,
            "statusCode": None,
            "finalUrl": url,
            "error": f"{type(error).__name__}:{error}",
            "text": "",
        }


def marker_found(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


def detect_platform_from_text(text: str) -> dict:
    checks = [
        ("shopify", "needs_review", ["cdn.shopify.com", "shopify.theme", "myshopify.com", "/cart/add"]),
        ("woocommerce", "needs_review", ["woocommerce", "wp-content/plugins/woocommerce", "wc-blocks"]),
        ("bigcommerce", "needs_review", ["bigcommerce", "cdn11.bigcommerce.com", "stencil-utils", "bigcommerce.stencil"]),
        ("prestashop", "needs_adapter", ["prestashop", "powered by prestashop", "/modules/ps_"]),
        ("magento", "needs_adapter", ["magento", "mage/", "magento_ui"]),
    ]
    for platform, status, markers in checks:
        if marker_found(text, markers):
            return {
                "platform": platform,
                "status": status,
                "evidence": f"Detected {platform} page markers",
            }
    return {
        "platform": "unknown",
        "status": "needs_review",
        "evidence": "No supported ecommerce markers detected",
    }


def detect_target(target: dict) -> dict:
    urls = [
        normalise_url(target.get("surfboardCategoryUrl")),
        normalise_url(target.get("website")),
    ]
    checked = []
    combined_text = []
    for url in [item for item in urls if item]:
        response = fetch_text(url)
        checked.append(
            {
                "url": url,
                "ok": response["ok"],
                "statusCode": response["statusCode"],
                "finalUrl": response["finalUrl"],
                "error": response.get("error", ""),
            }
        )
        if response["text"]:
            combined_text.append(response["text"])
    detected = detect_platform_from_text("\n".join(combined_text))
    return {
        "retailerSlug": target["retailerSlug"],
        "retailerName": target["retailerName"],
        "regionCode": target["regionCode"],
        "country": target["country"],
        "priority": target["priority"],
        "enabled": target["enabled"],
        "configuredPlatform": target.get("platform", "unknown"),
        "detectedPlatform": detected["platform"],
        "status": detected["status"],
        "evidence": detected["evidence"],
        "checkedUrls": checked,
    }


def main() -> None:
    targets = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    results = [detect_target(target) for target in targets]
    summary = {}
    for result in results:
        key = f"{result['status']}:{result['detectedPlatform']}"
        summary[key] = summary.get(key, 0) + 1
    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "purpose": "US retailer platform discovery only. No SQL import, no production table writes.",
        "regionCode": "US",
        "priceCurrency": "USD",
        "targetsChecked": len(results),
        "summary": summary,
        "results": results,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("US retailer discovery complete")
    print(f"Targets checked: {len(results)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
