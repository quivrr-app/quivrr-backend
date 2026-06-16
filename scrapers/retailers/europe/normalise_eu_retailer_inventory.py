from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path


DISCOVERY_FILES = [
    Path("scrapers/retailers/europe/magento/output/eu_magento_product_discovery.json"),
    Path("scrapers/retailers/europe/prestashop/output/eu_prestashop_product_discovery.json"),
    Path("scrapers/retailers/europe/custom/output/eu_custom_product_discovery.json"),
    Path("scrapers/retailers/europe/woocommerce/output/eu_woocommerce_product_discovery.json"),
]
OUTPUT_FILE = Path("scrapers/retailers/europe/output/eu_normalised_inventory.json")

REGION_CODE = "EU"
DEFAULT_PRICE_CURRENCY = "EUR"

KNOWN_BRANDS = [
    "Al Merrick",
    "Aloha",
    "Channel Islands",
    "Christenson",
    "DHD",
    "Firewire",
    "GO-Softboards",
    "Hayden Shapes",
    "Haydenshapes",
    "Indio",
    "JS",
    "JS Industries",
    "Lib Tech",
    "Lost",
    "Norden",
    "NSP",
    "Pukas",
    "Pyzel",
    "Rusty",
    "Sharpeye",
    "Slater Designs",
    "Torq",
    "Zeus",
]

CONSTRUCTION_PATTERNS = [
    ("PU", re.compile(r"(?<![a-z0-9])pu(?![a-z0-9])", re.IGNORECASE)),
    ("EPS", re.compile(r"(?<![a-z0-9])eps(?![a-z0-9])", re.IGNORECASE)),
    ("Epoxy", re.compile(r"(?<![a-z0-9])epoxy(?![a-z0-9])", re.IGNORECASE)),
    ("Carbon", re.compile(r"(?<![a-z0-9])carbon(?![a-z0-9])", re.IGNORECASE)),
    ("Spine-Tek", re.compile(r"spine\s*-?\s*tek", re.IGNORECASE)),
]

FIN_PATTERNS = [
    ("FCS II", re.compile(r"(?<![a-z0-9])fcs\s*(?:ii|2|ll)(?![a-z0-9])", re.IGNORECASE)),
    ("FCS", re.compile(r"(?<![a-z0-9])fcs(?![a-z0-9])", re.IGNORECASE)),
    ("Futures", re.compile(r"(?<![a-z0-9])futures?(?![a-z0-9])", re.IGNORECASE)),
    ("Twin", re.compile(r"(?<![a-z0-9])twin(?:\s*fin)?(?![a-z0-9])", re.IGNORECASE)),
    ("Thruster", re.compile(r"(?<![a-z0-9])(?:tri\s*fin|thruster)(?![a-z0-9])", re.IGNORECASE)),
    ("2 Fin", re.compile(r"(?<![a-z0-9])2\s*fin(?![a-z0-9])", re.IGNORECASE)),
]

LENGTH_PATTERNS = [
    re.compile(r"\b(?P<feet>[4-9]|1[0-2])\s*['’]\s*(?P<inches>\d{1,2})\s*(?:''|\"|”|in)?\b"),
    re.compile(r"\b(?P<feet>[4-9]|1[0-2])\s*ft\s*(?P<inches>\d{1,2})\s*(?:\"|”|in)?\b", re.IGNORECASE),
    re.compile(r"\b(?P<feet>[4-9]|1[0-2])\.(?P<inches>\d{1,2})\b"),
]
VOLUME_PATTERN = re.compile(
    r"(?:\b(?:volume|vol\.?)\s*[:\-]?\s*)?\b(?P<volume>(?:1[5-9]|[2-7]\d|8[0-5])(?:[\.,]\d{1,2})?)\s*(?:l|ltr|litre|litres)\b",
    re.IGNORECASE,
)


def clean(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def decimal_string(value: object) -> str | None:
    text = clean(value).replace("€", "").replace("EUR", "").strip()
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")

    if not text:
        return None

    try:
        return str(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def parse_length(text: str) -> str | None:
    for pattern in LENGTH_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        feet = int(match.group("feet"))
        inches = int(match.group("inches"))
        if 4 <= feet <= 12 and 0 <= inches <= 12:
            return f"{feet}'{inches}"

    return None


def parse_volume(text: str) -> float | None:
    match = VOLUME_PATTERN.search(text)
    if not match:
        return None

    try:
        return float(match.group("volume").replace(",", "."))
    except ValueError:
        return None


def first_pattern(text: str, patterns: list[tuple[str, re.Pattern]]) -> str | None:
    for value, pattern in patterns:
        if pattern.search(text):
            return value
    return None


def brand_from_title(title: str) -> str | None:
    title_lower = title.lower()
    for brand in sorted(KNOWN_BRANDS, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(brand.lower())}(?![a-z0-9])", title_lower):
            return brand
    return None


def clean_brand(value: object) -> str | None:
    text = clean(value)
    if not text:
        return None

    text = re.sub(r"\bsurfboards?\b", "", text, flags=re.IGNORECASE)
    return clean(text) or None


def parse_brand(row: dict) -> str | None:
    return clean_brand(row.get("brand") or row.get("vendor")) or brand_from_title(clean(row.get("productTitle")))


def parse_model(title: str, brand: str | None) -> str | None:
    model = title
    if brand:
        model = re.sub(rf"(?<![a-z0-9]){re.escape(brand)}(?:\s+Surfboards?)?(?![a-z0-9])", " ", model, flags=re.IGNORECASE)

    for pattern in [
        r"\bsurfboards?\b",
        r"\b(?:[4-9]|1[0-2])\s*['’]\s*\d{1,2}\s*(?:''|\"|”|in)?\b",
        VOLUME_PATTERN.pattern,
        r"\bpu\b|\beps\b|\bepoxy\b|\bcarbon\b|spine\s*-?\s*tek",
        r"\bfcs\s*(?:ii|2|ll)?\b|\bfutures?\b|\btwin(?:\s*fin)?\b|\btri\s*fin\b|\bthruster\b",
        r"\b(?:white|black|blue|red|orange|color|sand)\b",
    ]:
        model = re.sub(pattern, " ", model, flags=re.IGNORECASE)

    return clean(re.sub(r"[-|_/]+", " ", model)) or None


def stock_status(row: dict) -> str:
    status = clean(row.get("stockStatus"))
    if status:
        return status

    available = row.get("isAvailable")
    if available is True:
        return "in_stock"
    if available is False:
        return "out_of_stock"
    return ""


def is_importable_raw(row: dict) -> bool:
    has_stock = row.get("isAvailable") is not None or bool(clean(row.get("stockStatus")))
    has_dimension = bool(row.get("lengthFeetInches") or row.get("volumeLitres"))

    return all([
        clean(row.get("retailerSlug")),
        clean(row.get("retailerName")),
        clean(row.get("regionCode")) == REGION_CODE,
        clean(row.get("rawProductTitle")),
        clean(row.get("productUrl")),
        row.get("priceAmount") is not None,
        clean(row.get("priceCurrency")) == DEFAULT_PRICE_CURRENCY,
        has_stock,
        has_dimension,
    ])


def combined_text(row: dict) -> str:
    return clean(" ".join([
        clean(row.get("productTitle")),
        clean(row.get("brand")),
        clean(row.get("vendor")),
        clean(row.get("sku")),
        clean(row.get("sourceSnippet")),
    ]))


def normalise_row(row: dict) -> dict:
    title = clean(row.get("productTitle"))
    text = combined_text(row)
    brand = parse_brand(row)
    price_currency = clean(row.get("priceCurrency")) or DEFAULT_PRICE_CURRENCY
    normalised = {
        "retailerSlug": clean(row.get("retailerSlug")),
        "retailerName": clean(row.get("retailerName")),
        "regionCode": REGION_CODE,
        "country": clean(row.get("country")),
        "platform": clean(row.get("platform")),
        "sourceUrl": clean(row.get("sourceUrl")),
        "rawProductTitle": title,
        "brandName": brand,
        "modelName": parse_model(title, brand),
        "productUrl": clean(row.get("productUrl")),
        "productImageUrl": clean(row.get("productImageUrl")),
        "priceAmount": decimal_string(row.get("priceAmount")),
        "priceCurrency": price_currency,
        "isAvailable": row.get("isAvailable") if isinstance(row.get("isAvailable"), bool) else None,
        "stockStatus": stock_status(row),
        "sku": clean(row.get("sku")),
        "lengthFeetInches": parse_length(text),
        "volumeLitres": parse_volume(text),
        "construction": first_pattern(text, CONSTRUCTION_PATTERNS),
        "finSetup": first_pattern(text, FIN_PATTERNS),
        "parseConfidence": row.get("parseConfidence"),
        "discoveryStatus": clean(row.get("discoveryStatus")) or "accepted",
        "needsCanonicalReview": True,
        "importableRaw": False,
    }
    normalised["importableRaw"] = is_importable_raw(normalised)
    return normalised


def load_products(input_files: list[Path]) -> tuple[list[dict], list[str]]:
    products = []
    sources = []

    for path in input_files:
        if not path.exists():
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("products", [])
        if isinstance(rows, list):
            products.extend(rows)
            sources.append(str(path))

    return products, sources


def run_self_tests() -> None:
    cases = [
        ("5'11''", "5'11", None),
        ("6’0”", "6'0", None),
        ("Surfboard TORQ TET 7.2 MOD Fish", "7'2", None),
        ("PRO DIMS - 5’0 x 17.13 x 2.13 x 19.15L", "5'0", 19.15),
        ("Volume: 33,2 litres", None, 33.2),
    ]
    for text, expected_length, expected_volume in cases:
        if expected_length and parse_length(text) != expected_length:
            raise AssertionError(f"Length failed for {text}")
        if expected_volume and parse_volume(text) != expected_volume:
            raise AssertionError(f"Volume failed for {text}")
    print("Generic EU normaliser self-tests passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalise EU retailer discovery outputs without SQL writes.")
    parser.add_argument("--self-test", action="store_true", help="Run parser-only checks.")
    parser.add_argument("--input", action="append", default=[], help="Optional discovery JSON path. Can be passed more than once.")
    parser.add_argument("--retailer", default="", help="Optional retailerSlug filter.")
    args = parser.parse_args()

    if args.self_test:
        run_self_tests()
        return

    input_files = [Path(path) for path in args.input] if args.input else DISCOVERY_FILES
    products, sources = load_products(input_files)
    if args.retailer:
        products = [row for row in products if clean(row.get("retailerSlug")) == args.retailer]

    rows = [normalise_row(row) for row in products]
    by_retailer = Counter(row["retailerSlug"] for row in rows)
    importable_by_retailer = Counter(row["retailerSlug"] for row in rows if row["importableRaw"])

    report = {
        "purpose": "Generic EU retailer inventory normalisation only. No SQL import or RetailerInventory writes.",
        "inputFiles": sources,
        "regionCode": REGION_CODE,
        "priceCurrency": DEFAULT_PRICE_CURRENCY,
        "inputProducts": len(products),
        "normalisedRows": len(rows),
        "importableRawRows": sum(1 for row in rows if row["importableRaw"]),
        "rowsByRetailer": dict(sorted(by_retailer.items())),
        "importableRawByRetailer": dict(sorted(importable_by_retailer.items())),
        "rows": rows,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Generic EU normalisation complete")
    print(f"Input products: {len(products)}")
    print(f"Normalised rows: {len(rows)}")
    print(f"Importable raw rows: {report['importableRawRows']}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
