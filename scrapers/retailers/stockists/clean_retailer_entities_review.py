import json
import re
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_au_review.json")
OUTPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_clean_review.json")

BAD_EXACT = {
    "find your magic board",
    "shop surfboards",
    "softboards",
    "all surfboards",
    "surfskates",
    "new boards",
    "new south wales",
    "western australia",
    "shop all boards",
    "shortboard",
    "used boards",
    "2nd hand boards",
    "act range",
    "all longboards",
    "all shortboards",
    "all traction",
    "board care",
    "board finder",
    "board models",
    "board selector",
    "board socks",
    "board videos",
    "boards in stock",
    "contact us",
    "demo waiver",
    "front foot",
    "kids boards",
    "kids softboard range"
}

BAD_CONTAINS = [
    "free shipping",
    "homepage",
    "review",
    "waiver",
    "influences",
    "heritage series",
    "continued on",
    "beautifully crafted",
    "australian-built",
    "models",
    "range",
    "shipping",
    "contact",
    "login",
    "privacy",
    "cookie",
    "wishlist",
    "account",
    "filter",
    "sort",
    "facebook",
    "instagram",
    "youtube",
    ".jpg",
    ".png",
    ".webp"
]

BRAND_ONLY = [
    "album surf",
    "chilli surfboards",
    "christenson surfboards australia",
    "dark arts surf",
    "dark arts surfboards",
    "firewire surfboards - australia",
    "homepage - torq surfboards",
    "lost surfboards"
]

def clean_name(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    value = value.strip("–-:|")
    return value

def is_address_or_email(value):
    lower = value.lower()
    if "@" in lower:
        return True
    if re.search(r"\b\d{4}\b", value) and re.search(r"\b(nsw|qld|vic|wa|sa|tas|act|nt)\b", lower):
        return True
    if re.search(r"^\d+\s+", value):
        return True
    return False

def keep(value):
    name = clean_name(value)
    lower = name.lower()

    if not name:
        return False

    if lower in BAD_EXACT:
        return False

    if lower in BRAND_ONLY:
        return False

    if any(bad in lower for bad in BAD_CONTAINS):
        return False

    if is_address_or_email(name):
        return False

    if len(name) < 4 or len(name) > 70:
        return False

    if name.isupper() and len(name.split()) > 2:
        return False

    return True

def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    output = []
    seen = set()

    for item in data:
        name = clean_name(item.get("retailer_name", ""))

        if not keep(name):
            continue

        key = name.lower()

        if key in seen:
            continue

        seen.add(key)

        output.append({
            "retailer_name": name,
            "source_brands": item.get("source_brands", []),
            "brand_count": item.get("brand_count", 0),
            "location_status": item.get("location_status", "review")
        })

    output.sort(key=lambda x: (-x["brand_count"], x["retailer_name"].lower()))

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Input: {len(data)}")
    print(f"Clean review: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
