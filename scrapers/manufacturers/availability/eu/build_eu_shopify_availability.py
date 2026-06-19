from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

REGION_CODE = "EU"
SOURCE = "manufacturer_direct"
TARGETS = {
    "js_industries": ("JS Industries", "https://www.jsindustries.eu", "all-surfboards"),
    "pyzel": ("Pyzel", "https://europe.pyzelsurfboards.com", "all-surfboards"),
    "sharp_eye": ("Sharp Eye", "https://sharpeyesurfboardseurope.com", "shop-surfboards"),
    "rusty": ("Rusty", "https://rustysurfboards.eu", "surfboards"),
    "firewire": ("Firewire", "https://eu.firewiresurfboards.com", "prestige-surfboards"),
    "haydenshapes": ("Haydenshapes", "https://eu.haydenshapes.com", "in-stock-surfboards"),
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Quivrr-EU-MFA/1.0)"}

JS_MODEL_ALIASES = {
    "BIG BARON CLEAR": "Big Baron",
    "BIG BARON TAN": "Big Baron",
    "BULL RUN SOFTBOARD SAGE": "Bull Run Softboard",
    "GOLDEN CHILD ROUND EASY RIDER": "Golden Child Easy Rider",
    "MONSTA ROUND EASY RIDER": "Monsta Easy Rider",
    "MONSTA SQUASH EASY RIDER": "Monsta Easy Rider",
    "XERO FUSION X SERIES": "Xero Fusion",
    "XERO FUSION X SERIES EASY RIDER": "Xero Fusion Easy Rider",
}


def text(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", value).strip()


def dimensions(value):
    value = text(value).replace("″", '"').replace("’", "'")
    length = re.search(r"\b([4-9]|1[0-2])\s*['’]\s*(\d{1,2})", value)
    volume = re.search(r"\b(\d{2,3}(?:[.,]\d{1,2})?)\s*L\b", value, re.I)
    chunks = re.findall(r"(?:\d+\s+)?\d+/\d+|\d+(?:\.\d+)?", value[length.end():] if length else "")
    return (
        f"{length.group(1)}'{int(length.group(2))}" if length else None,
        chunks[0] if len(chunks) > 0 else None,
        chunks[1] if len(chunks) > 1 else None,
        float(volume.group(1).replace(",", ".")) if volume else None,
    )


def model_name(brand, title):
    value = text(title)
    if brand == "JS Industries":
        value = re.sub(
            r"^JS\s+(?:Surfboard|SoftBoard)\s+[4-9](?:'\d{1,2})?\s+",
            "",
            value,
            flags=re.I,
        )
        value = re.sub(r"\s*\|.*$", "", value)
        value = re.sub(r"\s+\dft\d{1,2}$", "", value, flags=re.I)
        value = re.sub(
            r"\s+(?:CARBOTUNE|HYFI\s*(?:2|3\.0)?|PU|PE|EPS)$",
            "",
            value,
            flags=re.I,
        )
        value = re.sub(r"\s+SQUASH$", "", value, flags=re.I)
        value = re.sub(r"\s+", " ", value).strip(" -")
        return JS_MODEL_ALIASES.get(value.upper(), value)
    value = re.sub(r"^(?:JS(?:\s+Industries)?|Rusty)\s+", "", value, flags=re.I)
    value = re.sub(r"^Surfboards?\s+", "", value, flags=re.I)
    value = re.sub(r"^[4-9]'\d{1,2}\s+", "", value)
    value = re.sub(r"\b(?:High Performance|Performance|Surfboard)\b", "", value, flags=re.I)
    value = re.sub(r"\s+[4-9]'\d{1,2}.*$", "", value)
    value = re.sub(r"\s+(?:HYFI\s*2|HYFI|PU|EPS|FutureFlex)$", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip(" -")


def construction(value):
    key = text(value).lower()
    for token, label in (("futureflex", "FutureFlex"), ("carbotune", "CarboTune"), ("helium", "Helium"), ("ibolic", "Ibolic"), ("hyfi", "HYFI"), ("softboard", "Softboard"), ("eps", "EPS"), (" pe ", "PE"), (" pu ", "PU")):
        if token in f" {key} ": return label
    return None


def fin_setup(value):
    key = text(value).lower()
    if "fcs ii" in key or "fcs2" in key: return "FCS II"
    if "future" in key: return "Futures"
    return None


def fetch_products(base, collection):
    products = []
    for page in range(1, 100):
        url = f"{base}/collections/{collection}/products.json?limit=250&page={page}"
        response = requests.get(url, headers=HEADERS, timeout=45)
        response.raise_for_status()
        batch = response.json().get("products", [])
        products.extend(batch)
        if len(batch) < 250: break
    return products


def build(slug):
    brand, base, collection = TARGETS[slug]
    products = fetch_products(base, collection)
    rows, seen, variants = [], set(), 0
    for product in products:
        description = text(product.get("body_html"))
        image = ((product.get("images") or [{}])[0]).get("src")
        for variant in product.get("variants", []):
            variants += 1
            if not variant.get("available"): continue
            variant_title = text(variant.get("title"))
            combined = f"{product.get('title', '')} {variant_title}"
            length, width, thickness, volume = dimensions(combined)
            if brand == "JS Industries" and " x " not in combined.lower():
                width = thickness = None
            key = (str(product.get("id")), str(variant.get("id")))
            if key in seen: continue
            seen.add(key)
            rows.append({
                "brandName": brand, "modelName": model_name(brand, product.get("title")),
                "rawProductTitle": text(product.get("title")), "productDescription": description,
                "lengthFeetInches": length, "width": width, "thickness": thickness,
                "volumeLitres": volume, "construction": construction(combined),
                "finSetup": fin_setup(combined), "tailShape": None,
                "productUrl": f"{base}/products/{product.get('handle')}?variant={variant.get('id')}",
                "productImageUrl": (variant.get("featured_image") or {}).get("src") or image,
                "priceAmount": float(variant["price"]) if variant.get("price") else None,
                "priceCurrency": "EUR", "stockStatus": "available", "isAvailable": True,
                "availabilitySource": SOURCE, "regionCode": REGION_CODE,
                "sourceProductId": str(product.get("id")), "sourceVariantId": str(variant.get("id")),
                "sourceVariantTitle": variant_title, "scrapedAtUtc": datetime.now(timezone.utc).isoformat(),
            })
    output = Path(f"scrapers/manufacturers/availability/{slug}/output/{slug}_eu_manufacturer_inventory.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"brand": brand, "platform": "Shopify", "sourceUrl": f"{base}/collections/{collection}",
            "rawProducts": len(products), "uniqueProducts": len({p.get('id') for p in products}),
            "variantsScanned": variants, "availableVariants": len(rows), "normalisedRows": len(rows),
            "rowsWithDimensions": sum(bool(r["lengthFeetInches"]) for r in rows),
            "rowsMissingDimensions": sum(not r["lengthFeetInches"] for r in rows), "output": str(output)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", choices=[*TARGETS, "all"], default="all")
    args = parser.parse_args()
    slugs = TARGETS if args.brand == "all" else [args.brand]
    diagnostics = [build(slug) for slug in slugs]
    path = Path("scrapers/manufacturers/availability/eu/output/eu_mfa_shopify_diagnostics.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__": main()
