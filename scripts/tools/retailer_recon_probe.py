import argparse
import asyncio
import csv
import json
import re
import socket
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


DEFAULT_TARGETS = [
    {"name": "Boardcave", "url": "https://www.boardcave.com.au"},
    {"name": "Natural Necessity", "url": "https://www.naturalnecessity.com.au"},
    {"name": "Surf FX", "url": "https://www.surffx.com.au"},
    {"name": "Strapper Surf", "url": "https://www.strapper.com.au"},
    {"name": "Kirra Surf", "url": "https://www.kirrasurf.com.au"},
    {"name": "Onboard Store", "url": "https://www.onboardstore.com.au"},
    {"name": "Nth Degree", "url": "https://www.nthdegree.com.au"},
    {"name": "12 Board Store", "url": "https://www.12boardstore.com.au"},
    {"name": "Bennys Boardroom", "url": "https://www.bennysboardroom.com.au"},
    {"name": "SDS Surf", "url": "https://www.sds.com.au"},
    {"name": "Sideways Surf", "url": "https://www.sideways.com.au"},
    {"name": "Seaside Surf Shop", "url": "https://www.seasidesurfshop.com.au"},
    {"name": "Riders Lodge", "url": "https://www.riderslodge.com.au"},
    {"name": "Momentum Surf", "url": "https://www.momentumsurf.com.au"},
    {"name": "Board Collectors", "url": "https://www.boardcollectors.com"},
    {"name": "Surfstitch", "url": "https://www.surfstitch.com"},
    {"name": "City Beach", "url": "https://www.citybeach.com"},
    {"name": "Ocean and Earth", "url": "https://www.oceanearthstore.com"},
    {"name": "Coastalwatch", "url": "https://www.coastalwatch.com"},
    {"name": "Mundo Surf", "url": "https://www.mundo-surf.com"},
    {"name": "Surf Dive n Ski", "url": "https://www.sds.com.au"},
    {"name": "Trigger Bros", "url": "https://www.triggerbrothers.com.au"},
    {"name": "Underground Surf", "url": "https://www.undergroundsurf.com.au"},
    {"name": "Le BAO", "url": "https://www.lebao.com.au"},
]

PROBE_PATHS = [
    "/",
    "/robots.txt",
    "/sitemap.xml",
    "/sitemap_products_1.xml",
    "/products.json?limit=250",
    "/collections/all/products.json?limit=250",
    "/collections/surfboards/products.json?limit=250",
    "/collections/surfboards",
    "/collections/boards",
    "/collections/surfboard",
    "/collections/all",
    "/products",
    "/shop",
    "/wp-json/wc/store/products?per_page=10",
    "/wp-json/wp/v2/product?per_page=10",
    "/api/products",
    "/search?q=surfboard",
    "/search?type=product&q=surfboard",
]

HEADERS = {
    "User-Agent": "Quivrr Inventory Research Bot/0.1; contact=hello@quivrr.app",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-AU,en;q=0.9",
}


@dataclass
class ProbeResult:
    retailer: str
    base_url: str
    final_url: str
    path: str
    status_code: int | None
    content_type: str
    server: str
    cdn_or_waf: str
    platform_signals: list[str]
    protection_signals: list[str]
    product_signals: list[str]
    title: str
    response_length: int
    error: str


def normalise_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url.rstrip("/")


def resolve_hostname(url: str) -> list[str]:
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return []
        return sorted({item[4][0] for item in socket.getaddrinfo(hostname, 443)})
    except Exception:
        return []


def detect_cdn_or_waf(headers: httpx.Headers, text: str) -> str:
    haystack = " ".join([
        headers.get("server", ""),
        headers.get("cf-ray", ""),
        headers.get("x-sucuri-id", ""),
        headers.get("x-cache", ""),
        headers.get("x-amz-cf-id", ""),
        headers.get("x-akamai-transformed", ""),
        headers.get("x-iinfo", ""),
        headers.get("x-datadome", ""),
        headers.get("x-px", ""),
        text[:3000],
    ]).lower()

    checks = [
        ("Cloudflare", ["cloudflare", "cf-ray", "__cf_bm", "cf-chl"]),
        ("Akamai", ["akamai", "akamai bot", "x-akamai"]),
        ("Imperva Incapsula", ["incapsula", "visid_incap", "x-iinfo"]),
        ("Sucuri", ["sucuri", "x-sucuri"]),
        ("Fastly", ["fastly", "x-served-by"]),
        ("AWS CloudFront", ["cloudfront", "x-amz-cf"]),
        ("DataDome", ["datadome", "x-datadome"]),
        ("PerimeterX", ["perimeterx", "_px", "px-captcha"]),
        ("Shopify Edge", ["shopify", "x-shopify"]),
    ]

    found = [name for name, tokens in checks if any(token in haystack for token in tokens)]
    return ", ".join(found) if found else ""


def detect_platform(headers: httpx.Headers, text: str, url: str) -> list[str]:
    h = " ".join([str(headers), text[:120000], url]).lower()
    found = []

    checks = [
        ("Shopify", ["cdn.shopify.com", "shopify.theme", "x-shopify", "myshopify.com", "/cart/add.js"]),
        ("WooCommerce", ["woocommerce", "wc-blocks", "wp-content/plugins/woocommerce", "wp-json/wc"]),
        ("WordPress", ["wp-content", "wp-includes", "wp-json"]),
        ("BigCommerce", ["bigcommerce", "stencil-utils", "cdn11.bigcommerce.com"]),
        ("Magento", ["mage/cookies", "magento", "x-magento"]),
        ("Squarespace", ["squarespace", "static1.squarespace.com"]),
        ("Wix", ["wixstatic.com", "x-wix"]),
        ("Salesforce Commerce Cloud", ["demandware", "sfcc", "salesforce commerce"]),
        ("Commerce Cloud", ["commerce cloud"]),
        ("Custom or unknown ecommerce", ["add to cart", "product-grid", "product-card"]),
    ]

    for name, tokens in checks:
        if any(token in h for token in tokens):
            found.append(name)

    return sorted(set(found))


def detect_protection(headers: httpx.Headers, text: str, status_code: int | None) -> list[str]:
    h = " ".join([str(headers), text[:20000]]).lower()
    found = []

    if status_code in [401, 403, 406, 407, 409, 412, 423, 429, 451, 503]:
        found.append(f"Blocking or challenge status {status_code}")

    checks = [
        ("Cloudflare challenge", ["cf-chl", "checking your browser", "cf-ray", "turnstile"]),
        ("Bot challenge", ["captcha", "bot detection", "access denied", "verify you are human"]),
        ("Geo restriction", ["not available in your country", "access from your location", "geo", "region restricted"]),
        ("Rate limiting", ["rate limit", "too many requests", "temporarily blocked"]),
        ("JavaScript required", ["enable javascript", "requires javascript", "please enable js"]),
        ("DataDome challenge", ["datadome", "ddcid"]),
        ("PerimeterX challenge", ["perimeterx", "px-captcha", "_px"]),
        ("Akamai bot protection", ["akamai bot", "abck", "bm_sz"]),
        ("Imperva challenge", ["incapsula", "visid_incap", "x-iinfo"]),
    ]

    for name, tokens in checks:
        if any(token in h for token in tokens):
            found.append(name)

    return sorted(set(found))


def detect_product_signals(text: str, content_type: str) -> list[str]:
    signals = []
    lower = text.lower()

    if "application/json" in content_type.lower():
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                if "products" in parsed:
                    signals.append("JSON products array")
                if "product" in parsed:
                    signals.append("JSON product object")
            if isinstance(parsed, list):
                signals.append("JSON list response")
        except Exception:
            pass

    if "<loc>" in lower and "sitemap" in lower:
        signals.append("XML sitemap")

    if any(token in lower for token in ["surfboard", "shortboard", "longboard", "fish surfboard", "js industries", "pyzel", "firewire"]):
        signals.append("Surfboard keyword content")

    if any(token in lower for token in ["price", "add to cart", "sold out", "in stock", "availability"]):
        signals.append("Retail product content")

    if "/products/" in lower:
        signals.append("Product URL references")

    if "schema.org/product" in lower or '"@type":"product"' in lower or '"@type": "product"' in lower:
        signals.append("Product schema")

    return sorted(set(signals))


def extract_title(text: str) -> str:
    try:
        soup = BeautifulSoup(text, "html.parser")
        if soup.title and soup.title.string:
            return re.sub(r"\s+", " ", soup.title.string).strip()[:180]
    except Exception:
        pass
    return ""


async def fetch(client: httpx.AsyncClient, retailer: dict[str, str], path: str) -> ProbeResult:
    base_url = normalise_url(retailer["url"])
    url = urljoin(base_url + "/", path.lstrip("/"))

    try:
        response = await client.get(url, follow_redirects=True)
        text = response.text or ""
        content_type = response.headers.get("content-type", "")
        server = response.headers.get("server", "")
        cdn_or_waf = detect_cdn_or_waf(response.headers, text)
        platform_signals = detect_platform(response.headers, text, str(response.url))
        protection_signals = detect_protection(response.headers, text, response.status_code)
        product_signals = detect_product_signals(text, content_type)

        return ProbeResult(
            retailer=retailer["name"],
            base_url=base_url,
            final_url=str(response.url),
            path=path,
            status_code=response.status_code,
            content_type=content_type,
            server=server,
            cdn_or_waf=cdn_or_waf,
            platform_signals=platform_signals,
            protection_signals=protection_signals,
            product_signals=product_signals,
            title=extract_title(text),
            response_length=len(response.content or b""),
            error="",
        )

    except Exception as exc:
        return ProbeResult(
            retailer=retailer["name"],
            base_url=base_url,
            final_url=url,
            path=path,
            status_code=None,
            content_type="",
            server="",
            cdn_or_waf="",
            platform_signals=[],
            protection_signals=[],
            product_signals=[],
            title="",
            response_length=0,
            error=str(exc),
        )


def summarise(results: list[ProbeResult]) -> list[dict[str, Any]]:
    grouped: dict[str, list[ProbeResult]] = {}

    for result in results:
        grouped.setdefault(result.retailer, []).append(result)

    summary = []

    for retailer, items in grouped.items():
        statuses = [item.status_code for item in items if item.status_code is not None]
        platforms = sorted({value for item in items for value in item.platform_signals})
        protections = sorted({value for item in items for value in item.protection_signals})
        product_signals = sorted({value for item in items for value in item.product_signals})
        wafs = sorted({item.cdn_or_waf for item in items if item.cdn_or_waf})
        useful_paths = [
            item.path for item in items
            if item.status_code and item.status_code < 400 and item.product_signals
        ]

        if any("JSON products array" in item.product_signals for item in items):
            recommended_next_step = "Likely structured product feed available. Build or fix feed scraper first."
        elif "Shopify" in platforms:
            recommended_next_step = "Shopify detected, but common feeds may be blocked or unavailable. Test collection handles and sitemap product URLs."
        elif "WooCommerce" in platforms:
            recommended_next_step = "WooCommerce detected. Build scraper around Store API, product sitemap, or product schema."
        elif protections:
            recommended_next_step = "Protection or restriction detected. Use public sitemap, retailer feed, approved API, affiliate feed, or manual partnership path."
        elif product_signals:
            recommended_next_step = "Product pages are visible. Build HTML parser or sitemap driven crawler."
        else:
            recommended_next_step = "No reliable product path found. Needs manual inspection."

        summary.append({
            "retailer": retailer,
            "base_url": items[0].base_url,
            "status_codes_seen": sorted(set(statuses)),
            "platforms": platforms,
            "cdn_or_waf": wafs,
            "protection_signals": protections,
            "product_signals": product_signals,
            "useful_paths": useful_paths[:10],
            "recommended_next_step": recommended_next_step,
        })

    return summary


def write_outputs(output_dir: Path, results: list[ProbeResult], summary: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_json = output_dir / "retailer_recon_raw.json"
    summary_json = output_dir / "retailer_recon_summary.json"
    summary_csv = output_dir / "retailer_recon_summary.csv"
    report_md = output_dir / "retailer_recon_report.md"

    raw_json.write_text(
        json.dumps([asdict(item) for item in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "retailer",
                "base_url",
                "status_codes_seen",
                "platforms",
                "cdn_or_waf",
                "protection_signals",
                "product_signals",
                "useful_paths",
                "recommended_next_step",
            ],
        )
        writer.writeheader()
        for row in summary:
            writer.writerow({
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
                for key, value in row.items()
            })

    lines = [
        "# Quivrr Retailer Recon Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "This report identifies ecommerce platforms, likely protection layers, blocked endpoints and usable public product paths.",
        "",
    ]

    for row in summary:
        lines.extend([
            f"## {row['retailer']}",
            "",
            f"URL: {row['base_url']}",
            "",
            f"Status codes: {', '.join(map(str, row['status_codes_seen'])) if row['status_codes_seen'] else 'None'}",
            "",
            f"Platform signals: {', '.join(row['platforms']) if row['platforms'] else 'None found'}",
            "",
            f"CDN or WAF: {', '.join(row['cdn_or_waf']) if row['cdn_or_waf'] else 'None found'}",
            "",
            f"Protection signals: {', '.join(row['protection_signals']) if row['protection_signals'] else 'None found'}",
            "",
            f"Product signals: {', '.join(row['product_signals']) if row['product_signals'] else 'None found'}",
            "",
            "Useful paths:",
        ])

        if row["useful_paths"]:
            for path in row["useful_paths"]:
                lines.append(f"* {path}")
        else:
            lines.append("* None found")

        lines.extend([
            "",
            f"Recommended next step: {row['recommended_next_step']}",
            "",
        ])

    report_md.write_text("\n".join(lines), encoding="utf-8")


async def run(args: argparse.Namespace) -> None:
    if args.targets:
        targets = json.loads(Path(args.targets).read_text(encoding="utf-8"))
    else:
        targets = DEFAULT_TARGETS

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output or f"retailer_recon_results_{timestamp}").resolve()

    timeout = httpx.Timeout(args.timeout)
    limits = httpx.Limits(max_connections=args.concurrency, max_keepalive_connections=args.concurrency)

    results: list[ProbeResult] = []

    async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, limits=limits) as client:
        for probe_round in range(1, args.rounds + 1):
            print(f"\nProbe round {probe_round} of {args.rounds}")
            print("=" * 60)

            tasks = []
            for retailer in targets:
                for path in PROBE_PATHS:
                    tasks.append(fetch(client, retailer, path))

            for index, task in enumerate(asyncio.as_completed(tasks), start=1):
                result = await task
                results.append(result)

                status = result.status_code if result.status_code is not None else "ERR"
                platform = ",".join(result.platform_signals) if result.platform_signals else ""
                protection = ",".join(result.protection_signals) if result.protection_signals else ""
                print(f"[{index}/{len(tasks)}] {result.retailer} {result.path} {status} {platform} {protection}")

            if probe_round < args.rounds:
                await asyncio.sleep(args.delay)

    summary = summarise(results)
    write_outputs(output_dir, results, summary)

    print("\nDone")
    print("=" * 60)
    print(f"Output folder: {output_dir}")
    print(f"Summary report: {output_dir / 'retailer_recon_report.md'}")
    print(f"Summary CSV:    {output_dir / 'retailer_recon_summary.csv'}")
    print(f"Raw JSON:       {output_dir / 'retailer_recon_raw.json'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", help="Optional JSON file containing retailer targets")
    parser.add_argument("--output", help="Optional output folder. Defaults to current folder with timestamp")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--delay", type=int, default=60)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()