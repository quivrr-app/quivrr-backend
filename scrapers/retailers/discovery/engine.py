from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


SUPPORTED_BRANDS = {
    "album": "Album",
    "channel islands": "Channel Islands",
    "chilli": "Chilli",
    "dhd": "DHD",
    "firewire": "Firewire",
    "haydenshapes": "Haydenshapes",
    "js": "JS Industries",
    "js industries": "JS Industries",
    "lost": "Lost",
    "pyzel": "Pyzel",
    "rusty": "Rusty",
    "sharp eye": "Sharp Eye",
    "sharpeye": "Sharp Eye",
}

BOARD_PATH_MARKERS = (
    "/collections/surfboards",
    "/surfboards",
    "/boards/surf",
)


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    headers: dict[str, str]


def fetch_text(
    url: str,
    *,
    timeout_seconds: float = 15.0,
    headers: dict[str, str] | None = None,
) -> FetchResult:
    response = requests.get(
        url,
        headers=headers or {"User-Agent": "Mozilla/5.0 (compatible; QuivrrDiscovery/1.0)"},
        timeout=timeout_seconds,
    )
    return FetchResult(
        url=response.url,
        status_code=response.status_code,
        text=response.text,
        headers=dict(response.headers),
    )


def detect_board_collective_shell(
    website: str,
    html: str,
    product_urls: list[str],
) -> str:
    website_host = urlparse(website).netloc.lower()
    if "boardcollective.com.au" in html.lower() and "boardcollective.com.au" not in website_host:
        return "Board Collective"
    for product_url in product_urls:
        if "boardcollective.com.au" in urlparse(product_url).netloc.lower():
            return "Board Collective"
    return ""


def detect_platform_from_html(website: str, html: str) -> dict[str, Any]:
    lowered = html.lower()
    if "cdn11.bigcommerce.com" in lowered or "cdn\\.bigcommerce\\.com" in lowered or "bigcommerce" in lowered:
        return {
            "platform": "bigcommerce",
            "status": "ready_bigcommerce",
            "evidence": "html_markers",
        }
    if "cdn.shopify.com" in lowered or "shopify" in lowered:
        return {
            "platform": "shopify",
            "status": "ready_shopify",
            "evidence": "html_markers",
        }
    if "woocommerce" in lowered or "wc/store" in lowered:
        return {
            "platform": "woocommerce",
            "status": "ready_woocommerce",
            "evidence": "html_markers",
        }
    return {
        "platform": "unknown",
        "status": "manual_review",
        "evidence": "no_supported_markers",
    }


def probe_category_urls(client: Any, website: str) -> list[str]:
    return []


def discover_board_category_urls(client: Any, website: str, html: str) -> list[str]:
    urls: list[str] = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE):
        absolute = urljoin(website, href)
        lowered = absolute.lower()
        if any(marker in lowered for marker in BOARD_PATH_MARKERS):
            urls.append(absolute)
    urls.extend(probe_category_urls(client, website))
    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _parse_price(text: str) -> str:
    visible_text = re.sub(r"<[^>]+>", " ", text)
    visible_text = re.sub(r"\s+", " ", visible_text)
    match = re.search(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{2})?)", visible_text)
    if not match:
        match = re.search(r"\b([0-9]{2,}[0-9,]*(?:\.[0-9]{2})?)\b", visible_text)
    if not match:
        return ""
    return match.group(1).replace(",", "")


def extract_product_candidates_from_html(html: str, page_url: str) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for block in re.findall(r"<article.*?</article>", html, flags=re.IGNORECASE | re.DOTALL):
        href_match = re.search(r'href=["\']([^"\']+)["\']', block, flags=re.IGNORECASE)
        if not href_match:
            continue
        title_match = re.search(r">([^<]+)</a>", block, flags=re.IGNORECASE)
        title = (title_match.group(1).strip() if title_match else "").strip()
        lowered = title.lower()
        if "fins" in lowered or "fin" == lowered:
            continue
        if "surfboard" not in lowered and "board" not in lowered:
            continue
        stock_status = ""
        lowered_block = re.sub(r"\s+", " ", block).lower()
        if "in stock" in lowered_block:
            stock_status = "in_stock"
        elif "sold out" in lowered_block:
            stock_status = "sold_out"
        image_match = re.search(r'src=["\']([^"\']+)["\']', block, flags=re.IGNORECASE)
        products.append(
            {
                "productTitle": title,
                "productUrl": urljoin(page_url, href_match.group(1)),
                "imageUrl": urljoin(page_url, image_match.group(1)) if image_match else "",
                "priceAmount": _parse_price(block),
                "stockStatus": stock_status,
            }
        )
    return products


def extract_supported_brand_signals(*texts: str) -> list[str]:
    found: list[str] = []
    haystack = " ".join(texts).lower()
    for token, canonical in SUPPORTED_BRANDS.items():
        if token in haystack and canonical not in found:
            found.append(canonical)
    return found


def classify_discovery_result(result: dict[str, Any]) -> dict[str, Any]:
    classified = dict(result)
    board_urls = result.get("boardCategoryUrls") or []
    product_examples = result.get("productUrlExamples") or []
    approx_count = int(result.get("approxBoardProductCount") or 0)
    platform = result.get("detectedPlatform") or "unknown"

    if any("/us/" in (url or "").lower() for url in board_urls + product_examples):
        classified["recommendedStatus"] = "manual_review"
        classified["manualReviewReason"] = "non_au_catalogue_surface"
        classified["confidence"] = "medium"
        classified["priorityScore"] = min(int(result.get("priorityScore") or 0), 30)
        return classified

    if platform == "bigcommerce" and approx_count >= 10 and result.get("priceVisible") and result.get("stockVisible"):
        classified["recommendedStatus"] = "ready_bigcommerce"
        classified["manualReviewReason"] = ""
        classified["confidence"] = "high"
        classified["priorityScore"] = max(int(result.get("priorityScore") or 0), 65)
        return classified

    classified["recommendedStatus"] = result.get("currentStatus") or "manual_review"
    classified["manualReviewReason"] = result.get("manualReviewReason", "")
    classified["confidence"] = "medium" if approx_count else "low"
    classified["priorityScore"] = int(result.get("priorityScore") or 0)
    return classified


def build_discovery_report(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    summary: dict[str, int] = {}
    for candidate in candidates:
        detected = classify_discovery_result(
            {
                "dealerName": candidate.get("dealerName", ""),
                "website": candidate.get("website", ""),
                "detectedPlatform": candidate.get("platform", "unknown"),
                "currentStatus": candidate.get("status", "manual_review"),
                "boardCategoryUrls": [],
                "productUrlExamples": [],
                "approxBoardProductCount": 0,
                "supportedBrandSignals": [],
                "priceVisible": False,
                "stockVisible": False,
                "imagesVisible": False,
                "dimensionsVisible": False,
                "volumeVisible": False,
                "paginationDetected": False,
                "duplicateOf": "",
                "blockedReason": "",
            }
        )
        results.append(detected)
        status = detected.get("recommendedStatus", "manual_review")
        summary[status] = summary.get(status, 0) + 1
    return {
        "candidateCount": len(candidates),
        "summary": summary,
        "results": results,
    }
