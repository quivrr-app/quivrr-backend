import re
from pathlib import Path

html_path = Path("scrapers/brands/lost/output/lost_speed_demon_inspect.html")

if not html_path.exists():
    html_path = Path("scrapers/brands/lost/output/speed_demon_page.html")

if not html_path.exists():
    html_path.write_text(
        __import__("requests").get(
            "https://lostsurfboards.net/surfboards/speed-demon/",
            headers={"User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)"},
            timeout=(10, 30),
        ).text,
        encoding="utf-8",
    )

html = html_path.read_text(encoding="utf-8", errors="ignore")

patterns = [
    "volume",
    "litre",
    "liter",
    "dimensions",
    "length",
    "width",
    "thickness",
    "5'",
    "5’",
    "6'",
    "6’",
    "Speed Demon",
    "size",
    "wp-content",
]

for pattern in patterns:
    print("")
    print("=" * 80)
    print("PATTERN:", pattern)
    print("=" * 80)

    matches = list(re.finditer(re.escape(pattern), html, flags=re.I))

    print("matches:", len(matches))

    for match in matches[:8]:
        start = max(0, match.start() - 300)
        end = min(len(html), match.end() + 500)
        snippet = html[start:end]
        snippet = re.sub(r"\s+", " ", snippet)
        print("")
        print(snippet[:1200])
