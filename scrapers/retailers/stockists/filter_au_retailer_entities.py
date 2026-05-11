import json
import re
from pathlib import Path

INPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities.json")
CANDIDATES_FILE = Path("scrapers/retailers/stockists/output/stockist_candidates.json")
OUTPUT_FILE = Path("scrapers/retailers/stockists/output/retailer_entities_au_review.json")

AU_SIGNALS = [
    "australia", " australian ", "nsw", "qld", "vic", "wa", "tas", "sa", "act", "nt",
    "new south wales", "queensland", "victoria", "western australia",
    "south australia", "tasmania", "canberra",
    "sydney", "manly", "brookvale", "collaroy", "narrabeen", "bondi", "cronulla",
    "newcastle", "central coast", "coffs harbour", "byron", "wollongong",
    "gold coast", "burleigh", "coolangatta", "mermaid beach", "noosa",
    "sunshine coast", "alexandra headland", "caloundra", "coolum",
    "torquay", "melbourne", "frankston", "mornington", "phillip island",
    "margaret river", "yallingup", "perth", "mandurah", "geraldton",
    "adelaide", "glenelg", "burnie", "hobart"
]

NON_AU_SIGNALS = [
    "usa", "united states", "california", "hawaii", "florida", "oregon",
    "new zealand", "nz", "europe", "france", "spain", "portugal",
    "uk", "united kingdom", "japan", "indonesia", "bali", "brazil",
    "canada", "mexico", "south africa"
]

def norm(value):
    return re.sub(r"\s+", " ", value or "").strip()

def score_au(text):
    lower = f" {text.lower()} "
    au_score = sum(1 for signal in AU_SIGNALS if signal in lower)
    non_au_score = sum(1 for signal in NON_AU_SIGNALS if signal in lower)
    return au_score, non_au_score

def main():
    retailers = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    candidates = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))

    brand_context = {}

    for entry in candidates:
        brand = entry.get("brand")
        text_blob = " ".join(entry.get("candidates", []))
        brand_context[brand] = text_blob

    output = []

    for retailer in retailers:
        name = retailer.get("retailer_name", "")
        source_brands = retailer.get("source_brands", [])

        context = name + " " + " ".join(source_brands)
        for brand in source_brands:
            context += " " + brand_context.get(brand, "")

        au_score, non_au_score = score_au(context)

        if au_score > 0 and non_au_score == 0:
            status = "likely_au"
        elif au_score > 0 and non_au_score > 0:
            status = "needs_review_mixed_signals"
        else:
            status = "unknown_location"

        if status in ["likely_au", "needs_review_mixed_signals"]:
            output.append({
                **retailer,
                "au_score": au_score,
                "non_au_score": non_au_score,
                "location_status": status
            })

    output.sort(key=lambda x: (x["location_status"], -x["brand_count"], x["retailer_name"].lower()))

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Input retailers: {len(retailers)}")
    print(f"AU review retailers: {len(output)}")
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
