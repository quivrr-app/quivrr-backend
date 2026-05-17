import json
import re
from pathlib import Path

import requests


TARGETS = [
    {
        "name": "Slimes Newcastle",
        "url": "https://www.slimesnewcastle.com.au/products.json?limit=250",
    },
    {
        "name": "Surfection",
        "url": "https://surfection.com/products.json?limit=250",
    },
    {
        "name": "Surfection Mosman",
        "url": "https://surfectionmosman.com/products.json?limit=250",
    },
    {
        "name": "Board Collective",
        "url": "https://boardcollective.com.au/products.json?limit=250",
    },
]


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


BOARD_WORDS = [
    "surfboard",
    "shortboard",
    "longboard",
    "mid length",
    "midlength",
    "fish",
    "twin",
    "step up",
    "step-up",
    "gun",
    "malibu",
    "softboard",
    "foamie",
]


def is_likely_board(product):
    text = " ".join([
        product.get("title", ""),
        product.get("body_html", ""),
        product.get("product_type", ""),
        " ".join(product.get("tags", [])),
        product.get("vendor", ""),
    ]).lower()

    if any(word in text for word in BOARD_WORDS):
        return True

    if re.search(r"\b[5-9]'?\d{0,2}\b", text):
        return True

    if re.search(r"\b\d{2}(\.\d)?\s?l\b", text):
        return True

    return False


results = []

for target in TARGETS:
    response = requests.get(
        target["url"],
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    products = response.json().get("products", [])

    likely_boards = [
        p for p in products
        if is_likely_board(p)
    ]

    result = {
        "name": target["name"],
        "url": target["url"],
        "total_products_first_page": len(products),
        "likely_boards_first_page": len(likely_boards),
        "sample_titles": [
            p.get("title")
            for p in likely_boards[:20]
        ],
    }

    results.append(result)

    print()
    print(target["name"])
    print("Total products first page:", len(products))
    print("Likely boards first page:", len(likely_boards))

    for title in result["sample_titles"][:10]:
        print(" -", title)


output = Path("scrapers/retailers/output/recon/final_four_shopify_product_probe.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(results, indent=2), encoding="utf-8")

print()
print("Probe complete.")
print("Output written to:", output)
