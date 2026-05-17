import requests

BASE_URL = "https://surfectionmosman.com"

handles = [
    "js-industries",
    "dhd",
    "sharpeye",
    "channel-islands",
    "haydenshapes",
    "tolhurst-x-harley-ingleby",
    "chilli",
    "lost",
    "volume",
    "joel-fitzgerald-surfboards",
    "global-surf-industries",
    "gerry-lopez",
    "ocean-soul",
    "gato",
]

for handle in handles:
    url = f"{BASE_URL}/collections/{handle}/products.json?limit=250"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)

    print()
    print(handle, r.status_code)

    if r.status_code == 200:
        products = r.json().get("products", [])
        print("products:", len(products))

        for product in products[:10]:
            print(" -", product.get("title"))
