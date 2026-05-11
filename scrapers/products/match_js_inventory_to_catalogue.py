from pathlib import Path
import json
import re

CATALOGUE_FILE = Path("scrapers/brands/output/js_master_catalogue.json")
INVENTORY_FILE = Path("scrapers/products/output/js_inventory_index.json")

OUTPUT_DIR = Path("scrapers/products/output")
OUTPUT_FILE = OUTPUT_DIR / "js_inventory_matched.json"


def clean(value):
    value = str(value or "").lower()
    value = value.replace("js industries", "")
    value = value.replace("js surfboards", "")
    value = value.replace("surfboard", "")
    value = re.sub(r"[^a-z0-9\.]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalise_length(value):
    value = str(value or "").lower().strip()
    value = value.replace('"', "")
    value = value.replace("ft", "'")
    value = value.replace(" ", "")
    return value


def normalise_model(value):
    value = clean(value)
    value = value.replace("raging bull", "raging bull")
    return value


def build_catalogue_keys(catalogue):
    keys = []

    for board in catalogue:
        keys.append({
            "catalogue_record": board,
            "model_clean": normalise_model(board.get("model")),
            "length_clean": normalise_length(board.get("length")),
            "volume_litres": board.get("volume_litres"),
            "construction_clean": clean(board.get("construction")),
            "fin_clean": clean(board.get("fin_system")),
        })

    return keys


def score_match(item, key):
    score = 0
    reasons = []

    title = clean(item.get("title"))
    model = clean(item.get("model"))
    length = normalise_length(item.get("length"))
    volume = item.get("volume_litres")
    construction = clean(item.get("construction"))
    fin = clean(item.get("fin_system"))

    search_text = f"{title} {model}"

    if key["model_clean"] and key["model_clean"] in search_text:
        score += 45
        reasons.append("model")

    if key["length_clean"] and key["length_clean"] == length:
        score += 20
        reasons.append("length")

    if key["volume_litres"] is not None and volume is not None:
        if abs(float(key["volume_litres"]) - float(volume)) <= 0.15:
            score += 20
            reasons.append("volume")

    if key["construction_clean"] and key["construction_clean"] == construction:
        score += 10
        reasons.append("construction")

    if key["fin_clean"] and key["fin_clean"] == fin:
        score += 5
        reasons.append("fin")

    return score, reasons


def main():
    catalogue = json.loads(CATALOGUE_FILE.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))

    catalogue_keys = build_catalogue_keys(catalogue)

    matched = []
    unmatched = []

    for item in inventory:
        best = None

        for key in catalogue_keys:
            score, reasons = score_match(item, key)

            if not best or score > best["score"]:
                best = {
                    "score": score,
                    "reasons": reasons,
                    "catalogue_record": key["catalogue_record"],
                }

        if best and best["score"] >= 65:
            matched.append({
                "match_score": best["score"],
                "match_reasons": best["reasons"],
                "catalogue": best["catalogue_record"],
                "inventory": item,
            })
        else:
            unmatched.append(item)

    OUTPUT_FILE.write_text(
        json.dumps(
            {
                "summary": {
                    "catalogue_records": len(catalogue),
                    "inventory_records": len(inventory),
                    "matched": len(matched),
                    "unmatched": len(unmatched),
                },
                "matched": matched,
                "unmatched": unmatched,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nJS inventory matching complete")
    print(f"Catalogue records: {len(catalogue)}")
    print(f"Inventory records: {len(inventory)}")
    print(f"Matched: {len(matched)}")
    print(f"Unmatched: {len(unmatched)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
        