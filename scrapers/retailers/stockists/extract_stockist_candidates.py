import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

BASE_DIR = Path("scrapers/retailers/stockists")
RAW_DIR = BASE_DIR / "raw"
OUTPUT_FILE = BASE_DIR / "output" / "stockist_candidates.json"

STATE_TERMS = [
    "NSW", "QLD", "VIC", "WA", "SA", "TAS", "NT", "ACT",
    "New South Wales", "Queensland", "Victoria", "Western Australia",
    "South Australia", "Tasmania"
]

STORE_KEYWORDS = [
    "surf", "surfboards", "board", "boards", "boardstore",
    "surfshop", "surf shop", "surfection", "empire", "sanbah",
    "strapper", "trigger", "beach beat", "kirra", "wicks",
    "aloha", "slimes", "natural necessity", "sideways"
]

def clean_text(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    return value

def looks_like_stockist(line):
    lower = line.lower()

    if len(line) < 4 or len(line) > 120:
        return False

    if any(keyword in lower for keyword in STORE_KEYWORDS):
        return True

    if any(state in line for state in STATE_TERMS):
        return True

    return False

def extract_candidates(file_path):
    html = file_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    text = soup.get_text("\n")
    lines = [clean_text(line) for line in text.splitlines()]
    lines = [line for line in lines if looks_like_stockist(line)]

    unique = []
    seen = set()

    for line in lines:
        key = line.lower()
        if key not in seen:
            seen.add(key)
            unique.append(line)

    return unique

def main():
    results = []

    for file_path in sorted(RAW_DIR.glob("*.html")):
        brand = file_path.stem.replace("_", " ").title()
        candidates = extract_candidates(file_path)

        results.append({
            "brand": brand,
            "raw_file": str(file_path),
            "candidate_count": len(candidates),
            "candidates": candidates[:300]
        })

        print(f"{brand}: {len(candidates)} candidates")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
