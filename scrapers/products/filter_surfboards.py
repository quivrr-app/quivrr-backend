import json
import re
from pathlib import Path
from urllib.parse import urlparse


INPUT_DIRS = [
    Path("scrapers/products/output/shopify"),
    Path("scrapers/products/output/woocommerce"),
    Path("scrapers/products/output/bigcommerce"),
    Path("scrapers/products/output/magento"),
    Path("scrapers/products/output/neto_maropost"),
    Path("scrapers/products/output/squarespace"),
    Path("scrapers/products/output/wix"),
    Path("scrapers/products/output/ecwid"),
]

OUTPUT_FILE = Path("scrapers/products/output/likely_surfboards.json")
REJECTED_FILE = Path("scrapers/products/output/rejected_products.json")
REPORT_FILE = Path("scrapers/products/output/surfboard_filter_report.json")

SURFBOARD_BOARD_TYPES = [
    "surfboard",
    "surf board",
    "shortboard",
    "longboard",
    "mid length",
    "midlength",
    "step up",
    "step-up",
    "softboard",
    "foamie",
    "foam board",
    "funboard",
    "malibu",
    "mini mal",
    "mini-mal",
    "gun",
    "fish",
    "twin fin",
    "twinfin",
    "performance board",
    "hybrid board",
]

SURFBOARD_BRANDS = [
    "js",
    "js industries",
    "channel islands",
    "ci surfboards",
    "lost",
    "lost surfboards",
    "mayhem",
    "pyzel",
    "firewire",
    "slater designs",
    "dhd",
    "haydenshapes",
    "hayden shapes",
    "sharp eye",
    "sharpeye",
    "chilli",
    "rusty",
    "album",
    "christenson",
    "pukas",
    "torq",
    "softlite",
    "mick fanning",
    "mick fanning softboards",
    "nsp",
    "aloha",
    "misfit",
    "dms",
    "simon anderson",
    "chemistry",
    "mctavish",
    "thunderbolt",
    "takayama",
    "walden",
    "bennetts",
    "creative army",
    "modern",
    "superbrand",
    "stacey",
    "dhdsurf",
]

BOARD_CONSTRUCTIONS = [
    "hyfi",
    "hyfi 3.0",
    "spinetek",
    "helium",
    "lft",
    "timbertek",
    "thunderbolt",
    "futureflex",
    "dark arts",
    "carbotune",
    "pu",
    "poly",
    "eps",
    "epoxy",
    "pe",
    "carbon",
    "soft tech",
    "softtech",
]

FIN_SYSTEMS = [
    "futures",
    "fcs",
    "fcs ii",
    "fcs2",
    "single fin",
    "2 plus 1",
    "thruster",
    "quad",
    "twin",
    "five fin",
    "5 fin",
]

HARD_EXCLUDE_TERMS = [
    "boardshort",
    "board short",
    "wetsuit",
    "spring suit",
    "springsuit",
    "steamer",
    "rash vest",
    "rashguard",
    "rash guard",
    "tee",
    "t-shirt",
    "shirt",
    "singlet",
    "hood",
    "hoodie",
    "fleece",
    "jumper",
    "jacket",
    "pants",
    "shorts",
    "dress",
    "bikini",
    "cap",
    "hat",
    "beanie",
    "sunscreen",
    "zinc",
    "wax",
    "comb",
    "legrope",
    "leg rope",
    "leash",
    "tail pad",
    "traction",
    "deck grip",
    "grip pad",
    "sticker",
    "towel",
    "poncho",
    "sock",
    "board sock",
    "cover",
    "stretch cover",
    "board cover",
    "board bag",
    "day bag",
    "travel bag",
    "coffin",
    "accessory",
    "accessories",
    "strap",
    "tie down",
    "roof rack",
    "wall rack",
    "board sling",
    "skate",
    "skateboard",
    "snowboard",
    "sunglasses",
    "watch",
    "gift card",
    "voucher",
    "repair kit",
    "ding repair",
    "ding all",
]

FIN_ACCESSORY_TERMS = [
    "fins",
    "fin set",
    "keel fin",
    "thruster fin",
    "quad fin",
    "single fin",
    "centre fin",
    "center fin",
    "side fins",
    "replacement fin",
]

PRICE_PATTERN = re.compile(r"^\d+(?:\.\d{1,2})?$")

LENGTH_PATTERN = re.compile(
    r"\b(?:[4-9]|1[0-2])\s*(?:'|’|ft)\s*\d{0,2}\b",
    re.IGNORECASE,
)

FULL_DIMENSION_PATTERN = re.compile(
    r"\b(?:[4-9]|1[0-2])\s*(?:'|’|ft)\s*\d{0,2}\s*"
    r"(?:\"|in)?\s*[xX*]\s*"
    r"\d{1,2}(?:\s+\d{1,2}/\d{1,2})?(?:\.\d+)?\s*"
    r"(?:\"|in)?\s*[xX*]\s*"
    r"\d(?:\s+\d{1,2}/\d{1,2})?(?:\.\d+)?",
    re.IGNORECASE,
)

LITRE_PATTERN = re.compile(
    r"\b(?:1[5-9]|[2-7]\d|8[0-5])(?:\.\d{1,2})?\s*(?:l|ltr|litre|litres)\b",
    re.IGNORECASE,
)

URL_BOARD_HINT_PATTERN = re.compile(
    r"(surfboard|surfboards|shortboard|longboard|midlength|mid-length|softboard|foamie)",
    re.IGNORECASE,
)


def clean_text(value):
    if value is None:
        return ""

    return str(value).replace("â€™", "’").lower().strip()


def text_blob(item):
    parts = [
        item.get("title"),
        item.get("variant_title"),
        item.get("vendor"),
        item.get("product_type"),
        item.get("sku"),
        item.get("handle"),
        item.get("url"),
        item.get("product_url"),
    ]

    return " ".join([clean_text(p) for p in parts if p])


def get_url(item):
    raw = item.get("url") or item.get("product_url") or ""

    return str(raw).strip()


def get_domain(item):
    raw = get_url(item)

    if not raw:
        return ""

    try:
        parsed = urlparse(raw)
        return parsed.netloc.lower()
    except Exception:
        return ""


def contains_phrase(text, phrases):
    return any(phrase in text for phrase in phrases)


def has_term_boundary(text, terms):
    for term in terms:
        pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"

        if re.search(pattern, text):
            return True

    return False


def has_hard_exclusion(text):
    return contains_phrase(text, HARD_EXCLUDE_TERMS)


def has_fin_accessory_exclusion(text):
    if contains_phrase(text, FIN_ACCESSORY_TERMS):
        if not contains_phrase(text, SURFBOARD_BOARD_TYPES):
            return True

    return False


def has_board_type(text):
    return contains_phrase(text, SURFBOARD_BOARD_TYPES)


def has_board_brand(text):
    return has_term_boundary(text, SURFBOARD_BRANDS)


def has_construction(text):
    return has_term_boundary(text, BOARD_CONSTRUCTIONS)


def has_fin_system(text):
    return has_term_boundary(text, FIN_SYSTEMS)


def has_board_url_hint(item):
    url = get_url(item)

    return bool(URL_BOARD_HINT_PATTERN.search(url))


def get_numeric_price(item):
    raw_price = item.get("price")

    if raw_price is None:
        return None

    price = str(raw_price).strip().replace("$", "").replace(",", "")

    if not PRICE_PATTERN.match(price):
        return None

    try:
        return float(price)
    except ValueError:
        return None


def has_realistic_price(item):
    price = get_numeric_price(item)

    if price is None:
        return True, "missing_or_unparsed_price"

    if price < 250:
        return False, "price_too_low"

    if price > 5000:
        return False, "price_too_high"

    return True, "price_ok"


def score_item(item):
    text = text_blob(item)

    result = {
        "is_surfboard": False,
        "confidence": 0,
        "reasons": [],
        "reject_reason": None,
    }

    if not text:
        result["reject_reason"] = "missing_text"
        return result

    if has_hard_exclusion(text):
        result["reject_reason"] = "hard_excluded_product_type"
        return result

    if has_fin_accessory_exclusion(text):
        result["reject_reason"] = "fin_accessory_not_board"
        return result

    price_ok, price_reason = has_realistic_price(item)

    if not price_ok:
        result["reject_reason"] = price_reason
        return result

    result["reasons"].append(price_reason)

    has_length = bool(LENGTH_PATTERN.search(text))
    has_full_dimensions = bool(FULL_DIMENSION_PATTERN.search(text))
    has_litres = bool(LITRE_PATTERN.search(text))
    board_type = has_board_type(text)
    brand = has_board_brand(text)
    construction = has_construction(text)
    fin_system = has_fin_system(text)
    url_hint = has_board_url_hint(item)

    if has_full_dimensions:
        result["confidence"] += 4
        result["reasons"].append("full_dimensions")

    if has_length:
        result["confidence"] += 2
        result["reasons"].append("length")

    if has_litres:
        result["confidence"] += 3
        result["reasons"].append("litres")

    if board_type:
        result["confidence"] += 3
        result["reasons"].append("board_type")

    if brand:
        result["confidence"] += 3
        result["reasons"].append("brand")

    if construction:
        result["confidence"] += 1
        result["reasons"].append("construction")

    if fin_system:
        result["confidence"] += 1
        result["reasons"].append("fin_system")

    if url_hint:
        result["confidence"] += 1
        result["reasons"].append("url_board_hint")

    strong_identity = brand and (
        board_type
        or has_full_dimensions
        or has_litres
    )

    strong_dimensions = has_full_dimensions and (
        has_litres
        or board_type
        or brand
    )

    strong_board_type = (
        board_type
        and (has_length or has_litres)
        and get_numeric_price(item) is not None
    )

    result["is_surfboard"] = (
        result["confidence"] >= 6
        and (
            strong_identity
            or strong_dimensions
            or strong_board_type
        )
    )

    if not result["is_surfboard"]:
        result["reject_reason"] = "low_confidence_or_missing_board_identity"

    return result


def enrich_item(item, score):
    enriched = dict(item)
    enriched["surfboard_confidence"] = score["confidence"]
    enriched["surfboard_match_reasons"] = score["reasons"]
    enriched["retailer_domain"] = get_domain(item)

    return enriched


def load_items(file_path):
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            if isinstance(data.get("products"), list):
                return data["products"]

            if isinstance(data.get("items"), list):
                return data["items"]

        return []

    except Exception as exc:
        print(f"{file_path.name}: failed to read JSON: {exc}")
        return []


def main():
    accepted = []
    rejected = []
    total_items = 0
    file_results = []

    for input_dir in INPUT_DIRS:
        if not input_dir.exists():
            file_results.append({
                "directory": str(input_dir),
                "status": "missing",
                "raw": 0,
                "accepted": 0,
                "rejected": 0,
            })

            continue

        json_files = sorted(input_dir.glob("*.json"))

        if not json_files:
            file_results.append({
                "directory": str(input_dir),
                "status": "empty",
                "raw": 0,
                "accepted": 0,
                "rejected": 0,
            })

            continue

        for file_path in json_files:
            items = load_items(file_path)
            total_items += len(items)

            file_accepted = 0
            file_rejected = 0

            for item in items:
                score = score_item(item)

                if score["is_surfboard"]:
                    accepted.append(enrich_item(item, score))
                    file_accepted += 1
                else:
                    rejected_item = enrich_item(item, score)
                    rejected_item["surfboard_reject_reason"] = score["reject_reason"]
                    rejected.append(rejected_item)
                    file_rejected += 1

            file_results.append({
                "file": str(file_path),
                "platform_directory": str(input_dir),
                "raw": len(items),
                "accepted": file_accepted,
                "rejected": file_rejected,
            })

            print(
                f"{file_path.name}: "
                f"{len(items)} raw -> "
                f"{file_accepted} verified surfboards, "
                f"{file_rejected} rejected"
            )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(
            accepted,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    REJECTED_FILE.write_text(
        json.dumps(
            rejected[:5000],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = {
        "input_directories": [
            str(input_dir)
            for input_dir in INPUT_DIRS
        ],
        "raw_items": total_items,
        "verified_surfboards": len(accepted),
        "rejected_products_sample": min(len(rejected), 5000),
        "accepted_output": str(OUTPUT_FILE),
        "rejected_output": str(REJECTED_FILE),
        "files": file_results,
    }

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print(f"Raw items: {total_items}")
    print(f"Verified surfboards: {len(accepted)}")
    print(f"Rejected sample saved: {min(len(rejected), 5000)}")
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Rejected sample: {REJECTED_FILE}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()