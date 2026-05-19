from pathlib import Path


path = Path("scrapers/brands/christenson/discover_christenson_model_links.py")

text = path.read_text(encoding="utf-8")

old = '''
        bad_terms = [
            "/about",
            "/team",
            "/store",
            "/custom",
            "/where-to-buy",
            "/news",
            "/shipping",
            "/cart",
            "/account",
            "mailto:",
        ]
'''

new = '''
        bad_terms = [
            "#main-content",
            "/about",
            "/team",
            "/store",
            "/shop",
            "/surfboard-stock",
            "/custom",
            "/where-to-buy",
            "/news",
            "/shipping",
            "/cart",
            "/account",
            "/apparel",
            "/fins",
            "/gift-cards",
            "/wetsuits",
            "/snowboards",
            "/yowskateboards",
            "/used-boards",
            "/used-boards-and-accessories",
            "/united-states",
            "/canada",
            "/japan",
            "/australia",
            "/europe",
            "/bali",
            "/taiwan",
            "/costa-rica",
            "/instock-",
            "mailto:",
        ]
'''

if old not in text:
    raise RuntimeError("Could not find bad_terms block")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("Patched Christenson junk link filtering")
