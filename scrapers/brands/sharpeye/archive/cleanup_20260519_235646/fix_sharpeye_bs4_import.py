from pathlib import Path

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")
text = path.read_text(encoding="utf-8")

if "from bs4 import BeautifulSoup" not in text:
    text = text.replace(
        "import requests",
        "import requests\nfrom bs4 import BeautifulSoup",
        1
    )

path.write_text(text, encoding="utf-8")

print("Added BeautifulSoup import")
