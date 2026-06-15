from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path


INPUT_FILE = Path(
    "scrapers/retailers/europe/shopify/output/eu_shopify_product_discovery.json"
)
OUTPUT_FILE = Path(
    "scrapers/retailers/europe/shopify/output/eu_shopify_normalised_inventory.json"
)

REGION_CODE = "EU"
DEFAULT_PRICE_CURRENCY = "EUR"
SOURCE_PLATFORM = "shopify"

WORKING_RETAILERS = {
    "bell_surf": {
        "retailerName": "Bell Surf",
        "country": "Portugal",
    },
    "board_exchange": {
        "retailerName": "Board Exchange",
        "country": "Portugal",
    },
    "guincho_wind_factory": {
        "retailerName": "Guincho Wind Factory",
        "country": "Portugal",
    },
    "hart_beach": {
        "retailerName": "Hart Beach",
        "country": "Netherlands",
    },
    "santoloco": {
        "retailerName": "SantoLoco",
        "country": "Germany",
    },
}

KNOWN_BRANDS = [
    "Album",
    "Aloha",
    "Buster",
    "Channel Islands",
    "Christenson",
    "Chilli",
    "DHD",
    "Firewire",
    "Flowt",
    "Grace",
    "Haydenshapes",
    "Indio",
    "JS Industries",
    "KT",
    "Lib Tech",
    "Lost",
    "McTavish",
    "Mick Fanning",
    "NSP",
    "Pukas",
    "Pyzel",
    "Quiksilver",
    "Rusty",
    "Sharpeye",
    "Slater Designs",
    "Torq",
]

CONSTRUCTION_PATTERNS = [
    ("PU", re.compile(r"(?<![a-z0-9])pu(?![a-z0-9])", re.IGNORECASE)),
    ("EPS", re.compile(r"(?<![a-z0-9])eps(?![a-z0-9])", re.IGNORECASE)),
    ("Epoxy", re.compile(r"(?<![a-z0-9])epoxy(?![a-z0-9])", re.IGNORECASE)),
    ("Carbon", re.compile(r"(?<![a-z0-9])carbon(?![a-z0-9])", re.IGNORECASE)),
]

FIN_PATTERNS = [
    ("FCS II", re.compile(r"(?<![a-z0-9])fcs\s*(?:ii|2)(?![a-z0-9])", re.IGNORECASE)),
    ("FCS", re.compile(r"(?<![a-z0-9])fcs(?![a-z0-9])", re.IGNORECASE)),
    ("Futures", re.compile(r"(?<![a-z0-9])futures?(?![a-z0-9])", re.IGNORECASE)),
    ("2 Fin", re.compile(r"(?<![a-z0-9])2\s*fin(?![a-z0-9])", re.IGNORECASE)),
    ("Twin", re.compile(r"(?<![a-z0-9])twin(?:\s*fin)?(?![a-z0-9])", re.IGNORECASE)),
    ("Thruster", re.compile(r"(?<![a-z0-9])thruster(?![a-z0-9])", re.IGNORECASE)),
]

LENGTH_PATTERNS = [
    re.compile(
        r"\b(?P<feet>[4-9]|1[0-2])\s*['’]\s*(?P<inches>\d{1,2})"
        r"\s*(?:''|\"|”|in)?\b",
    ),
    re.compile(
        r"\b(?P<feet>[4-9]|1[0-2])\s*ft\s*(?P<inches>\d{1,2})"
        r"\s*(?:\"|”|in)?\b",
        re.IGNORECASE,
    ),
]

COMPACT_LENGTH_PATTERN = re.compile(
    r"\b(?P<feet>[4-9]|1[0-2])(?P<inches>0[0-9]|1[0-2])\b"
)

VOLUME_PATTERN = re.compile(
    r"(?:\b(?:volume|vol\.?)\s*[:\-]?\s*)?"
    r"\b(?P<volume>(?:1[5-9]|[2-7]\d|8[0-5])(?:[\.,]\d{1,2})?)\s*"
    r"(?:l|ltr|litre|litres)\b",
    re.IGNORECASE,
)

MODEL_VOLUME_PATTERN = re.compile(
    r"\b(?:1[5-9]|[2-7]\d|8[0-5])(?:[\.,]\d{1,2})?\s*"
    r"(?:l|ltr|litre|litres)\b",
    re.IGNORECASE,
)

SURFBOARD_TERMS = [
    "surfboard",
    "surfboards",
    "surf board",
    "shortboard",
    "longboard",
    "malibu",
    "fish",
    "mini mal",
    "midlength",
    "mid length",
    "twin fin",
]


def clean(value: object) -> str:
    if value is None:
        return ""

    return str(value).strip()


def compact_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def decimal_string(value: object) -> str | None:
    text = clean(value).replace(",", "")

    if not text:
        return None

    try:
        return str(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def combined_text(item: dict) -> str:
    values = [
        item.get("productTitle"),
        item.get("vendor"),
        item.get("brand"),
        item.get("rawHandle"),
        " ".join(item.get("variantTitles") or []),
        " ".join(item.get("optionNames") or []),
    ]

    return compact_spaces(" ".join(clean(value) for value in values if clean(value)))


def normalise_length_match(feet: str, inches: str) -> str | None:
    try:
        feet_number = int(feet)
        inches_number = int(inches)
    except ValueError:
        return None

    if not 4 <= feet_number <= 12:
        return None

    if not 0 <= inches_number <= 12:
        return None

    return f"{feet_number}'{inches_number}"


def parse_length(text: str) -> str | None:
    for pattern in LENGTH_PATTERNS:
        match = pattern.search(text)

        if match:
            return normalise_length_match(
                match.group("feet"),
                match.group("inches"),
            )

    compact_match = COMPACT_LENGTH_PATTERN.search(text)

    if compact_match:
        return normalise_length_match(
            compact_match.group("feet"),
            compact_match.group("inches"),
        )

    return None


def parse_volume(text: str) -> float | None:
    match = VOLUME_PATTERN.search(text)

    if not match:
        return None

    try:
        return float(match.group("volume").replace(",", "."))
    except ValueError:
        return None


def parse_first_pattern(text: str, patterns: list[tuple[str, re.Pattern]]) -> str | None:
    for value, pattern in patterns:
        if pattern.search(text):
            return value

    return None


def brand_from_title(title: str) -> str | None:
    title_lower = title.lower()

    for brand in sorted(KNOWN_BRANDS, key=len, reverse=True):
        brand_key = brand.lower()

        if re.search(rf"(?<![a-z0-9]){re.escape(brand_key)}(?![a-z0-9])", title_lower):
            return brand

    return None


def clean_brand_name(value: str) -> str | None:
    brand = compact_spaces(value)

    if not brand:
        return None

    brand = re.sub(r"\bsurfboards?\b", "", brand, flags=re.IGNORECASE)
    brand = compact_spaces(brand)

    return brand or None


def parse_brand(item: dict) -> str | None:
    title_brand = brand_from_title(clean(item.get("productTitle")))

    if title_brand:
        return title_brand

    vendor = clean_brand_name(clean(item.get("vendor") or item.get("brand")))

    return vendor


def strip_brand(title: str, brand: str | None) -> str:
    if not brand:
        return title

    brand_terms = [
        brand,
        f"{brand} Surfboards",
        f"{brand} Surfboard",
    ]

    result = title

    for term in sorted(brand_terms, key=len, reverse=True):
        result = re.sub(
            rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])",
            " ",
            result,
            flags=re.IGNORECASE,
        )

    return compact_spaces(result)


def parse_model_name(title: str, brand: str | None) -> str | None:
    model = strip_brand(title, brand)

    remove_patterns = [
        r"\bsurfboards?\b",
        r"\b(?:[4-9]|1[0-2])\s*['’]\s*\d{1,2}\s*(?:''|\"|”|in)?\b",
        r"\b(?:[4-9]|1[0-2])\s*ft\s*\d{1,2}\s*(?:\"|”|in)?\b",
        MODEL_VOLUME_PATTERN.pattern,
        r"\bpu\b",
        r"\beps\b",
        r"\bepoxy\b",
        r"\bcarbon\b",
        r"\bfcs\s*(?:ii|2)?\b",
        r"\bfutures?\b",
        r"\b2\s*fin\b",
        r"\btwin(?:\s*fin)?\b",
        r"\bthruster\b",
    ]

    for pattern in remove_patterns:
        model = re.sub(pattern, " ", model, flags=re.IGNORECASE)

    model = re.sub(r"[-|_/]+", " ", model)
    model = compact_spaces(model)

    return model or None


def stock_status(is_available: bool | None) -> str:
    if is_available is True:
        return "available"

    if is_available is False:
        return "unavailable"

    return "unknown"


def is_working_retailer(item: dict) -> bool:
    return clean(item.get("retailerSlug")) in WORKING_RETAILERS


def normalise_item(item: dict) -> dict:
    retailer_slug = clean(item.get("retailerSlug"))
    retailer = WORKING_RETAILERS[retailer_slug]
    title = clean(item.get("productTitle"))
    text = combined_text(item)
    brand = parse_brand(item)
    is_available = item.get("availability")

    return {
        "retailerSlug": retailer_slug,
        "retailerName": clean(item.get("retailerName")) or retailer["retailerName"],
        "regionCode": REGION_CODE,
        "country": retailer["country"],
        "brandName": brand,
        "modelName": parse_model_name(title, brand),
        "rawProductTitle": title,
        "productUrl": clean(item.get("productUrl")) or None,
        "productImageUrl": clean(item.get("productImageUrl")) or None,
        "priceAmount": decimal_string(item.get("priceAmount")),
        "priceCurrency": clean(item.get("priceCurrency")) or DEFAULT_PRICE_CURRENCY,
        "isAvailable": is_available if isinstance(is_available, bool) else None,
        "stockStatus": stock_status(is_available),
        "lengthFeetInches": parse_length(text),
        "volumeLitres": parse_volume(text),
        "construction": parse_first_pattern(text, CONSTRUCTION_PATTERNS),
        "finSetup": parse_first_pattern(text, FIN_PATTERNS),
        "sourcePlatform": SOURCE_PLATFORM,
        "parseConfidence": item.get("parseConfidence"),
    }


def load_products() -> list[dict]:
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    products = data.get("products", [])

    if not isinstance(products, list):
        raise RuntimeError("Discovery output products field must be a list.")

    return products


def run_self_tests() -> None:
    length_cases = [
        ("5'11''", "5'11"),
        ("5’11", "5'11"),
        ("5ft 11", "5'11"),
        ("5'11 x 19 1/2 x 2 3/8", "5'11"),
        ("6’0”", "6'0"),
        ("Pukas Leopard Fish Surfboard 5'6", "5'6"),
        ("Buster 5’3 FX-Type Featherlight Epoxy", "5'3"),
    ]

    volume_cases = [
        ("33.2 L", 33.2),
        ("33.2L", 33.2),
        ("33,2 L", 33.2),
        ("Volume: 33.2 litres", 33.2),
        ("Vol. 33.2L", 33.2),
        ("Torq Mod Fish 5'11'' | 33.2 L", 33.2),
    ]

    construction_cases = [
        ("Buster 5’3 FX-Type Featherlight Epoxy", "Epoxy"),
        ("KT AR PU Epoxy", "PU"),
        ("EPS Carbon rail", "EPS"),
    ]

    fin_cases = [
        ("Flying Diamond - FCS II 2 Fin", "FCS II"),
        ("Futures thruster setup", "Futures"),
        ("Twin fin fish", "Twin"),
        ("Classic Thruster", "Thruster"),
    ]

    failures = []

    for text, expected in length_cases:
        actual = parse_length(text)

        if actual != expected:
            failures.append(f"length {text!r}: expected {expected!r}, got {actual!r}")

    for text, expected in volume_cases:
        actual = parse_volume(text)

        if actual != expected:
            failures.append(f"volume {text!r}: expected {expected!r}, got {actual!r}")

    for text, expected in construction_cases:
        actual = parse_first_pattern(text, CONSTRUCTION_PATTERNS)

        if actual != expected:
            failures.append(
                f"construction {text!r}: expected {expected!r}, got {actual!r}"
            )

    for text, expected in fin_cases:
        actual = parse_first_pattern(text, FIN_PATTERNS)

        if actual != expected:
            failures.append(f"fin {text!r}: expected {expected!r}, got {actual!r}")

    if failures:
        raise AssertionError("\n".join(failures))

    print("EU Shopify parser self-tests passed")
    print(f"Length cases: {len(length_cases)}")
    print(f"Volume cases: {len(volume_cases)}")
    print(f"Construction cases: {len(construction_cases)}")
    print(f"Fin setup cases: {len(fin_cases)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalise EU Shopify discovery output without SQL writes."
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run parser-only self-tests without reading or writing discovery output.",
    )

    args = parser.parse_args()

    if args.self_test:
        run_self_tests()
        return

    products = load_products()
    normalised = [
        normalise_item(item)
        for item in products
        if item.get("suspectedSurfboard") is True and is_working_retailer(item)
    ]

    report = {
        "inputFile": str(INPUT_FILE),
        "regionCode": REGION_CODE,
        "sourcePlatform": SOURCE_PLATFORM,
        "workingRetailers": sorted(WORKING_RETAILERS),
        "inputProducts": len(products),
        "normalisedRows": len(normalised),
        "rows": normalised,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("EU Shopify normalisation complete")
    print(f"Input products: {len(products)}")
    print(f"Normalised rows: {len(normalised)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
