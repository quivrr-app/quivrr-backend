import json
import re
from pathlib import Path

import requests


TARGETS = [
    {
        "name": "Slimes Newcastle",
        "url": "https://www.slimesnewcastle.com.au/collections/surfboards/products.json?limit=250",
    },
    {
        "name": "Surfection",
        "url": "https://surfection.com/collections/surfboards/products.json?limit=250",
    },
    {
        "name": "Surfection Mosman",
        "url": "https://surfectionmosman.com/collections/surfboards/products.json?limit=250",
    },
    {
        "name": "Board Collective",
        "url": "https://boardcollective.com.au/collections/surfboards/products.json?limit=250",
    },
]


EXCLUDE_WORDS = [
    "wetsuit",
    "boardshort",
    "bottle",
    "tee",
    "shirt",
    "jacket",
    "sunglasses",
    "wax",
    "remover",
    "hat",
    "cap",
    "pants",
    "crew",
    "one piece",
    "bikini",
    "towel",
    "traction",
    "tail pad",
    "leash",
    "fins",
]


INCLUDE_WORDS = [
    "surfboard",
    "shortboard",
    "longboard",
    "mid length",
    "midlength",
    "fish",
    "twin fin",
    "softboard",
    "malibu",
    "log",
    "gun",
    "step up",
    "step-up",
    "js ",
    "pyzel",
    "channel islands",
    "ci ",
    "lost",
    "firewire",
    "dhd",
    "haydenshapes",
    "chilli",
    "sharp eye",
    "mctavish",
    "thunderbolt",
    "san juan",
]


def is_likely_board(product):
    text = " ".join([
        product.get("title", ""),
        product.get("product_type", ""),
        product.get("vendor", ""),
        " ".join(product.get("tags", [])),
    ]).lower()

    if any(word in text for word in EXCLUDE_WORDS):
        return False

    if any(word in text for word in INCLUDE_WORDS):
        return True

    if re.search(r"\b[5-9]'\d{1,2}", text):
        return True

    if re.search(r"\b\d{2}(\.\d)?\s?l\b", text):
        return True

    return False


results = []

for target in TARGETS:
    response = requests.get(
        target["url"],
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )

    response.raise_for_status()

    products = response.json().get("products", [])

    likely_boards = [
        p for p in products
        if is_likely_board(p)
    ]

    print()
    print(target["name"])
    print("Collection products:", len(products))
    print("Likely boards:", len(likely_boards))

    for product in likely_boards[:25]:
        print(" -", product.get("title"))

    results.append({
        "name": target["name"],
        "url": target["url"],
        "collection_products": len(products),
        "likely_boards": len(likely_boards),
        "sample_titles": [p.get("title") for p in likely_boards[:50]],
    })


output = Path("scrapers/retailers/output/recon/final_four_surfboards_collection_probe.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(results, indent=2), encoding="utf-8")

print()
print("Probe complete.")
print("Output written to:", output)
