from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
from datetime import datetime, timezone
from fractions import Fraction
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


def surf_fraction(value):
    number = float(value)
    whole = int(number)
    fraction = Fraction(number - whole).limit_denominator(16)
    if not fraction.numerator:
        return str(whole)
    return f"{whole} {fraction.numerator}/{fraction.denominator}"


def js_dimensions(tags):
    tag_text = " ".join(text(tag) for tag in (tags or []))
    match = re.search(
        r"\b([4-9]|1[0-2])\s*ft\s*(\d{1,2})\s*x\s*"
        r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)",
        tag_text,
        re.I,
    )
    if not match:
        return None, None, None
    return (
        f"{match.group(1)}'{int(match.group(2))}",
        surf_fraction(match.group(3)),
        surf_fraction(match.group(4)),
    )


def js_parent_handle(model):
    return re.sub(r"[^a-z0-9]+", "-", text(model).lower()).strip("-")


def last_assignment(block, name):
    matches = re.findall(rf"\b{re.escape(name)}\s*=\s*'([^']*)'", block)
    return text(matches[-1]) if matches else None


def parse_js_parent_inventory(page_html, parent_product):
    decoder = json.JSONDecoder()
    marker = "var board = "
    entries = {}
    position = 0
    parent_variants = parent_product.get("variants", [])
    while True:
        position = page_html.find(marker, position)
        if position < 0:
            break
        json_start = position + len(marker)
        try:
            board, consumed = decoder.raw_decode(page_html[json_start:])
        except json.JSONDecodeError:
            position = json_start
            continue
        block_start = page_html.rfind('var model = "";', 0, position)
        block = page_html[block_start if block_start >= 0 else max(0, position - 5000):position]
        construction_name = last_assignment(block, "construction")
        fin_system = last_assignment(block, "finSystem")
        tail_shape = last_assignment(block, "tail")
        length_metric = last_assignment(block, "boardLength")
        volume = last_assignment(block, "boardVolume")
        width_match = re.findall(r"boardWidth\s*=\s*parseFloat\('([^']+)'\)", block)
        thickness_match = re.findall(r"boardThickness\s*=\s*parseFloat\('([^']+)'\)", block)
        length_match = re.fullmatch(r"([4-9]|1[0-2])ft(\d{1,2})", length_metric or "", re.I)

        matching_parent_variants = []
        for variant in parent_variants:
            options = [text(option).lower() for option in variant.get("options", [])]
            if construction_name and not any(construction_name.lower() == option for option in options):
                continue
            if fin_system and not any(fin_system.lower() == option for option in options):
                continue
            if tail_shape and not any(tail_shape.lower() == option for option in options):
                continue
            matching_parent_variants.append(variant)
        parent_variant = matching_parent_variants[0] if len(matching_parent_variants) == 1 else None
        stock_variant = (board.get("variants") or [{}])[0]
        entries[str(board.get("id"))] = {
            "lengthFeetInches": (
                f"{length_match.group(1)}'{int(length_match.group(2))}"
                if length_match else None
            ),
            "width": surf_fraction(width_match[-1]) if width_match else None,
            "thickness": surf_fraction(thickness_match[-1]) if thickness_match else None,
            "volumeLitres": float(volume) if volume and re.fullmatch(r"\d+(?:\.\d+)?", volume) else None,
            "construction": construction_name,
            "finSetup": fin_system,
            "tailShape": tail_shape,
            "stockVariantId": str(stock_variant.get("id") or ""),
            "stockAvailable": bool(stock_variant.get("available")),
            "parentVariant": parent_variant,
        }
        position = json_start + consumed
    return entries


def fetch_js_parent(model, base):
    handle = js_parent_handle(model)
    url = f"{base}/products/{handle}"
    page = requests.get(url, headers=HEADERS, timeout=45)
    if page.status_code != 200:
        return model, handle, {}
    product_response = requests.get(f"{url}.js", headers=HEADERS, timeout=45)
    if product_response.status_code != 200:
        return model, handle, {}
    parent_product = product_response.json()
    return model, handle, parse_js_parent_inventory(page.text, parent_product)


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
    js_parent_data = {}
    if brand == "JS Industries":
        models = sorted({model_name(brand, product.get("title")) for product in products})
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            for model, handle, entries in pool.map(
                lambda item: fetch_js_parent(item, base), models
            ):
                js_parent_data[model] = {"handle": handle, "entries": entries}
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
            parsed_model = model_name(brand, product.get("title"))
            parent_variant = None
            stock_variant_id = str(variant.get("id"))
            if brand == "JS Industries":
                tag_length, tag_width, tag_thickness = js_dimensions(product.get("tags"))
                length = tag_length or length
                width = tag_width
                thickness = tag_thickness
                parent = js_parent_data.get(parsed_model, {})
                metadata = parent.get("entries", {}).get(str(product.get("id")), {})
                length = metadata.get("lengthFeetInches") or length
                width = metadata.get("width") or width
                thickness = metadata.get("thickness") or thickness
                volume = metadata.get("volumeLitres")
                parent_variant = metadata.get("parentVariant")
                if metadata:
                    variant_title = text(
                        (parent_variant or {}).get("title") or variant_title
                    )
            key = (str(product.get("id")), str(variant.get("id")))
            if key in seen: continue
            seen.add(key)
            rows.append({
                "brandName": brand, "modelName": parsed_model,
                "rawProductTitle": text(product.get("title")), "productDescription": description,
                "lengthFeetInches": length, "width": width, "thickness": thickness,
                "volumeLitres": volume,
                "construction": metadata.get("construction") if brand == "JS Industries" and metadata else construction(combined),
                "finSetup": metadata.get("finSetup") if brand == "JS Industries" and metadata else fin_setup(combined),
                "tailShape": metadata.get("tailShape") if brand == "JS Industries" and metadata else None,
                "productUrl": (
                    f"{base}/products/{parent.get('handle')}?variant={parent_variant.get('id')}"
                    if brand == "JS Industries" and parent_variant
                    else f"{base}/products/{product.get('handle')}?variant={variant.get('id')}"
                ),
                "productImageUrl": (
                    ((parent_variant or {}).get("featured_image") or {}).get("src")
                    or (variant.get("featured_image") or {}).get("src") or image
                ),
                "priceAmount": (
                    float(parent_variant["price"]) / 100
                    if parent_variant and isinstance(parent_variant.get("price"), int)
                    else float(variant["price"]) if variant.get("price") else None
                ),
                "priceCurrency": "EUR", "stockStatus": "available", "isAvailable": True,
                "availabilitySource": SOURCE, "regionCode": REGION_CODE,
                "sourceProductId": str(product.get("id")),
                "sourceVariantId": str(parent_variant.get("id")) if parent_variant else stock_variant_id,
                "sourceVariantTitle": variant_title, "scrapedAtUtc": datetime.now(timezone.utc).isoformat(),
                "sourceStockVariantId": stock_variant_id,
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
