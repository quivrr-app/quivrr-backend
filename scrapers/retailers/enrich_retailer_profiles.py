import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


INPUT_FILE = Path("scrapers/retailers/retailer_seed_clean.json")
OUTPUT_FILE = Path("scrapers/retailers/retailer_profiles_enriched.json")

TIMEOUT_SECONDS = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def normalise_url(base_url, value):
    value = clean(value)

    if not value:
        return None

    return urljoin(base_url, value)


def get_domain(url):
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return None


def fetch_html(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT_SECONDS,
            allow_redirects=True,
        )

        if response.status_code >= 400:
            return None, response.status_code, str(response.url)

        return response.text, response.status_code, str(response.url)

    except Exception as exc:
        return None, None, str(exc)


def find_favicon(soup, base_url):
    icon_selectors = [
        "link[rel='icon']",
        "link[rel='shortcut icon']",
        "link[rel='apple-touch-icon']",
        "link[rel='apple-touch-icon-precomposed']",
    ]

    for selector in icon_selectors:
        tag = soup.select_one(selector)

        if tag and tag.get("href"):
            return normalise_url(base_url, tag.get("href"))

    return urljoin(base_url, "/favicon.ico")


def score_logo_candidate(url):
    text = url.lower()

    score = 0

    if "logo" in text:
        score += 5

    if "brand" in text:
        score += 2

    if "header" in text:
        score += 2

    if "footer" in text:
        score += 1

    if "icon" in text:
        score -= 2

    if "payment" in text:
        score -= 5

    if "afterpay" in text or "paypal" in text or "visa" in text or "mastercard" in text:
        score -= 10

    if text.endswith(".svg"):
        score += 3

    if text.endswith(".png"):
        score += 2

    if text.endswith(".webp"):
        score += 1

    return score


def find_logo_url(soup, base_url):
    candidates = []

    meta_selectors = [
        "meta[property='og:logo']",
        "meta[name='logo']",
        "meta[itemprop='logo']",
    ]

    for selector in meta_selectors:
        tag = soup.select_one(selector)

        if tag:
            value = tag.get("content")

            if value:
                candidates.append(normalise_url(base_url, value))

    image_tags = soup.find_all("img")

    for img in image_tags:
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        alt = clean(img.get("alt")) or ""
        class_name = " ".join(img.get("class") or [])

        combined = f"{src or ''} {alt} {class_name}".lower()

        if not src:
            continue

        if "logo" in combined or "brand" in combined or "site-header" in combined:
            candidates.append(normalise_url(base_url, src))

    svg_tags = soup.find_all("svg")

    if svg_tags:
        for svg in svg_tags:
            label = " ".join(svg.get("class") or []) + " " + str(svg.get("aria-label") or "")

            if "logo" in label.lower():
                return None

    candidates = [item for item in candidates if item]

    if not candidates:
        return None

    candidates = sorted(
        set(candidates),
        key=lambda item: score_logo_candidate(item),
        reverse=True,
    )

    return candidates[0]


def find_contact_url(soup, base_url):
    links = soup.find_all("a", href=True)

    for link in links:
        href = link.get("href")
        text = link.get_text(" ", strip=True).lower()
        combined = f"{href} {text}".lower()

        if "contact" in combined:
            return normalise_url(base_url, href)

    return None


def find_social_url(soup, base_url, platform):
    links = soup.find_all("a", href=True)

    for link in links:
        href = link.get("href")
        text = link.get_text(" ", strip=True).lower()
        combined = f"{href} {text}".lower()

        if platform in combined:
            return normalise_url(base_url, href)

    return None


def enrich_retailer(retailer):
    website = clean(retailer.get("website"))

    enriched = dict(retailer)
    enriched["domain"] = get_domain(website)
    enriched["logo_url"] = None
    enriched["favicon_url"] = None
    enriched["contact_url"] = None
    enriched["instagram_url"] = None
    enriched["facebook_url"] = None
    enriched["enrichment_status"] = "not_started"
    enriched["http_status"] = None
    enriched["resolved_url"] = website

    if not website:
        enriched["enrichment_status"] = "missing_website"
        return enriched

    html, status_code, resolved_url = fetch_html(website)

    enriched["http_status"] = status_code
    enriched["resolved_url"] = resolved_url

    if not html:
        enriched["enrichment_status"] = "fetch_failed"
        return enriched

    soup = BeautifulSoup(html, "html.parser")
    base_url = resolved_url or website

    enriched["logo_url"] = find_logo_url(soup, base_url)
    enriched["favicon_url"] = find_favicon(soup, base_url)
    enriched["contact_url"] = find_contact_url(soup, base_url)
    enriched["instagram_url"] = find_social_url(soup, base_url, "instagram")
    enriched["facebook_url"] = find_social_url(soup, base_url, "facebook")

    if enriched["logo_url"] or enriched["favicon_url"]:
        enriched["enrichment_status"] = "enriched"
    else:
        enriched["enrichment_status"] = "no_logo_found"

    return enriched


def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    enriched = []

    print("")
    print("Enriching retailer profiles...")
    print(f"Input retailers: {len(retailers)}")
    print("")

    for index, retailer in enumerate(retailers, start=1):
        name = retailer.get("name")
        website = retailer.get("website")

        result = enrich_retailer(retailer)
        enriched.append(result)

        print(
            f"{index}/{len(retailers)} "
            f"{name} "
            f"status={result.get('enrichment_status')} "
            f"logo={bool(result.get('logo_url'))} "
            f"favicon={bool(result.get('favicon_url'))}"
        )

    OUTPUT_FILE.write_text(
        json.dumps(enriched, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logo_count = sum(1 for item in enriched if item.get("logo_url"))
    favicon_count = sum(1 for item in enriched if item.get("favicon_url"))

    print("")
    print(f"Retailers enriched: {len(enriched)}")
    print(f"Logo URLs found: {logo_count}")
    print(f"Favicon URLs found: {favicon_count}")
    print(f"Saved: {OUTPUT_FILE}")
    print("")


if __name__ == "__main__":
    main()