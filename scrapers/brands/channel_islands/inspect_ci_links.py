import json
from pathlib import Path

path = Path("scrapers/brands/channel_islands/output/ci_product_links.json")
items = json.loads(path.read_text(encoding="utf-8"))

for item in items[:10]:
    print("")
    print(item["slug"])
    print(item["title_hint"])
    print(item["product_url"])
