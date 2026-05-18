import requests

for base in [
    "https://rustysurfboards.com",
    "https://rustysurfboards.eu",
]:
    print("")
    print("=" * 80)
    print(base)
    print("=" * 80)

    for path in [
        "/collections/all-boards/products.json?limit=5",
        "/collections/surfboards/products.json?limit=5",
        "/products/rusty-1984-hybrid-surfboard.json",
        "/products/rusty-slayer-performance-surfboard.json",
    ]:
        url = base + path
        try:
            r = requests.get(url, timeout=(10, 30))
            print(r.status_code, url, r.headers.get("content-type"))

            if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
                data = r.json()
                product = data.get("product") or (data.get("products") or [None])[0]
                if product:
                    print(" title:", product.get("title"))
                    print(" handle:", product.get("handle"))
                    print(" variants:", len(product.get("variants", [])))
                    for v in product.get("variants", [])[:12]:
                        print("  -", v.get("title"), "|", v.get("option1"), "|", v.get("option2"), "|", v.get("option3"))
        except Exception as e:
            print("ERROR", url, e)
