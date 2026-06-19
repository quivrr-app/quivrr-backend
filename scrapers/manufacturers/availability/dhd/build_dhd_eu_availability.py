from __future__ import annotations

import concurrent.futures
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag

import requests
from bs4 import BeautifulSoup

BASE = "https://www.dhdsurf.eu"
CATEGORY = f"{BASE}/gb/510-surfboards"
OUTPUT = Path(
    "scrapers/manufacturers/availability/dhd/output/"
    "dhd_eu_manufacturer_inventory.json"
)
DIAGNOSTIC = Path(
    "scrapers/manufacturers/availability/dhd/output/dhd_eu_diagnostic.json"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Quivrr-EU-MFA/1.0)"}

MODEL_ALIASES = {
    "EE JULIETTE EPS": "EE Juliette",
    "EE JULIETTE RT": "EE Juliette",
    "INTERCEPTOR EPS": "Interceptor",
    "MINI TWIN EPS": "Mini Twin",
    "PHOENIX SWALLOW EPS": "Phoenix EPS Swallow Tail",
    "TWIN FIN": "The Twin",
    "UTOPIA EPS": "Utopia",
}


def clean(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", value).strip()


def model_name(title):
    value = clean(title)
    value = re.sub(r"^DHD\s+(?:EPS\s+)?(?:PRO|CORE|TRAVEL|SUMMER)\s+SERIES?\s+", "", value, flags=re.I)
    value = re.sub(r"\s+-\s+(?:BLACK|YELLOW|GREEN|TEAL).*?SPRAY$", "", value, flags=re.I)
    value = re.sub(r"\s+(?:PU\s+)?(?:FCS|FUTURES)$", "", value, flags=re.I)
    value = clean(value)
    return MODEL_ALIASES.get(value.upper(), value)


def dimensions(value):
    value = clean(value).replace("’", "'")
    length = re.search(r"([4-9]|1[0-2])\s*'\s*(\d{1,2})", value)
    volume = re.search(r"(\d{2,3}(?:[.,]\d+)?)\s*L\b", value, re.I)
    if not length:
        return None, None, None, None
    rest = value[length.end():]
    parts = [clean(part) for part in re.split(r"\s+x\s+", rest.lstrip(" -"), flags=re.I)]
    width = parts[0].split(" - ")[0] if parts else None
    thickness = parts[1].split(" - ")[0] if len(parts) > 1 else None
    return (
        f"{length.group(1)}'{int(length.group(2))}", width or None, thickness or None,
        float(volume.group(1).replace(",", ".")) if volume else None,
    )


def fetch_product(url):
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    title = clean((soup.select_one("h1") or soup.title).get_text(" ", strip=True))
    product_id = (soup.select_one('input[name="id_product"]') or {}).get("value")
    description = clean((soup.select_one("#description") or soup.select_one(".product-description-short") or ""))
    size_select = soup.select_one('select[name^="group["]')
    group_name = size_select.get("name") if size_select else None
    options = [
        (option.get("value"), clean(option.get_text(" ", strip=True)))
        for option in (size_select.select("option") if size_select else [])
        if option.get("value") and not option.has_attr("disabled")
    ]
    return {"url": url, "title": title, "productId": product_id, "description": description,
            "groupName": group_name, "options": options}


def fetch_variant(job):
    product, option_id, option_title = job
    data = {"id_product": product["productId"], "id_customization": "0", "qty": "1",
            product["groupName"]: option_id}
    response = requests.post(
        product["url"] + "?ajax=1&action=refresh", data=data,
        headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"}, timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    cart = clean(payload.get("product_add_to_cart"))
    available = "data-button-action=\"add-to-cart\"" in payload.get("product_add_to_cart", "")
    price_match = re.search(r'data-price="([0-9.]+)"', payload.get("product_prices", ""))
    cover = BeautifulSoup(payload.get("product_cover_thumbnails", ""), "html.parser").select_one("img")
    length, width, thickness, volume = dimensions(option_title)
    title = product["title"]
    construction = "EPS" if "EPS" in title.upper() else "PU"
    fin = "Futures" if "FUTURES" in title.upper() else "FCS II" if "FCS" in title.upper() else None
    return {
        "brandName": "DHD", "modelName": model_name(title), "rawProductTitle": title,
        "productDescription": product["description"], "lengthFeetInches": length,
        "width": width, "thickness": thickness, "volumeLitres": volume,
        "construction": construction, "finSetup": fin, "tailShape": None,
        "productUrl": payload.get("product_url") or product["url"],
        "productImageUrl": cover.get("src") if cover else None,
        "priceAmount": float(price_match.group(1)) if price_match else None,
        "priceCurrency": "EUR", "stockStatus": "available" if available else "out_of_stock",
        "isAvailable": available, "availabilitySource": "manufacturer_direct",
        "regionCode": "EU", "sourceProductId": product["productId"],
        "sourceVariantId": str(payload.get("id_product_attribute") or option_id),
        "sourceVariantTitle": option_title, "scrapedAtUtc": datetime.now(timezone.utc).isoformat(),
        "availabilityEvidence": cart[:200],
    }


def main():
    category = requests.get(CATEGORY, headers=HEADERS, timeout=45)
    category.raise_for_status()
    soup = BeautifulSoup(category.text, "html.parser")
    urls = sorted({
        urldefrag(link.get("href"))[0]
        for link in soup.select("article.product-miniature h2 a[href]")
    })
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        products = list(pool.map(fetch_product, urls))
    jobs = [(product, option_id, option_title) for product in products
            for option_id, option_title in product["options"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        variants = list(pool.map(fetch_variant, jobs))
    rows = [row for row in variants if row["isAvailable"]]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    report = {
        "platform": "PrestaShop", "sourceUrls": [CATEGORY], "rawProducts": len(urls),
        "uniqueProducts": len(products), "variants": len(variants),
        "availableVariants": len(rows), "normalisedMfaRows": len(rows),
        "rowsWithDimensions": sum(bool(row["lengthFeetInches"]) for row in rows),
        "rowsMissingDimensions": sum(not row["lengthFeetInches"] for row in rows),
    }
    DIAGNOSTIC.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
