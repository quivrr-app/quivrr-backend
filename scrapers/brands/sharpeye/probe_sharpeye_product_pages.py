from pathlib import Path
import re
import requests
from bs4 import BeautifulSoup

urls = [
    "https://sharpeyesurfboards.com/products/inferno-73",
    "https://sharpeyesurfboards.com/products/disco-ii-1",
    "https://sharpeyesurfboards.com/products/holy-toledo",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}

out = Path("scrapers/brands/sharpeye/output/sharpeye_product_page_probe.txt")
out.parent.mkdir(parents=True, exist_ok=True)

lines = []

for url in urls:
    r = requests.get(url, headers=headers, timeout=(10, 30))
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    lines.append("=" * 100)
    lines.append(url)
    lines.append(f"Status: {r.status_code}")
    lines.append(f"Title: {soup.title.get_text(' ', strip=True) if soup.title else None}")

    matches = re.findall(
        r"\d+'\s*\d{1,2}\"?\s*x\s*\d+(?:\.\d+)?(?:\s+\d+/\d+)?\s*x\s*\d+(?:\.\d+)?(?:\s+\d+/\d+)?\s*x\s*\d+(?:\.\d+)?\s*L",
        text,
        flags=re.IGNORECASE,
    )

    lines.append(f"Dimension matches: {len(matches)}")

    for match in matches[:30]:
        lines.append(f" - {match}")

    lines.append("")
    lines.append(text[:3000])
    lines.append("")

out.write_text("\n".join(lines), encoding="utf-8")

print(out)
print("Done")
