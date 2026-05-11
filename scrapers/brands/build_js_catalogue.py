from pathlib import Path
import json
import re

INPUT_FILE = Path("scrapers/products/output/shopify/js_industries.json")

OUTPUT_DIR = Path("scrapers/brands/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "js_master_catalogue.json"


def is_real_board(item):
    title = str(item.get("title", ""))

    if "Custom Order" in title:
        return False

    has_volume = re.search(r"\d+\.\d+L", title)
    has_length = re.search(r"\d{1,2}'\d{1,2}", title)

    return bool(has_volume and has_length)


def clean_dimension(value):
    if not value:
        return None

    value = str(value).replace('"', "")
    value = re.sub(r"\s+", " ", value).strip()

    return value


def parse_board(title):
    title = re.sub(r"\s+", " ", title).strip()

    model_match = re.match(r"^(.*?)\s+\d{1,2}'\d{1,2}", title)

    if not model_match:
        return None

    model = model_match.group(1).strip()

    dims_match = re.search(
        r"(\d{1,2}'\d{1,2}\"?)\s*[xX]\s*"
        r"(\d+(?:\s+\d+/\d+)?(?:\.\d+)?\"?)\s*[xX]\s*"
        r"(\d+(?:\s+\d+/\d+)?(?:\.\d+)?\"?)\s*-",
        title,
        re.IGNORECASE
    )

    volume_match = re.search(r"(\d+\.\d+)L", title)

    construction_match = re.search(
        r"(HYFI 3\.0|Carbotune|PU|PE|EPS|Softboard)",
        title,
        re.IGNORECASE
    )

    fin_match = re.search(
        r"(FCS 2|Futures)",
        title,
        re.IGNORECASE
    )

    tail_match = re.search(
        r"(Swallow|Squash|Round|Pin)",
        title,
        re.IGNORECASE
    )

    return {
        "model": model,
        "length": clean_dimension(dims_match.group(1)) if dims_match else None,
        "width": clean_dimension(dims_match.group(2)) if dims_match else None,
        "thickness": clean_dimension(dims_match.group(3)) if dims_match else None,
        "volume_litres": float(volume_match.group(1)) if volume_match else None,
        "construction": construction_match.group(1) if construction_match else None,
        "fin_system": fin_match.group(1) if fin_match else None,
        "tail_shape": tail_match.group(1) if tail_match else None,
    }


def variant_key(board):
    return "|".join([
        board.get("model") or "",
        board.get("length") or "",
        board.get("width") or "",
        board.get("thickness") or "",
        str(board.get("volume_litres") or ""),
        board.get("construction") or "",
        board.get("fin_system") or "",
    ])


def main():
    raw = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    boards = []

    for item in raw:
        if not is_real_board(item):
            continue

        parsed = parse_board(item.get("title", ""))

        if not parsed:
            continue

        images = item.get("images") or []

        parsed["brand"] = "JS Industries"
        parsed["price"] = item.get("price")
        parsed["available"] = item.get("available")
        parsed["product_url"] = item.get("product_url")
        parsed["image_url"] = images[0] if images else None

        boards.append(parsed)

    deduped = {}

    for board in boards:
        deduped[variant_key(board)] = board

    final_catalogue = sorted(
        deduped.values(),
        key=lambda x: (
            x["model"],
            x["length"] or "",
            x["volume_litres"] or 0
        )
    )

    OUTPUT_FILE.write_text(
        json.dumps(final_catalogue, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nJS catalogue built successfully")
    print(f"Raw products: {len(raw)}")
    print(f"Parsed boards: {len(boards)}")
    print(f"Canonical variants: {len(final_catalogue)}")

    print("\nFirst 20 entries:\n")

    for board in final_catalogue[:20]:
        print(
            f"{board['model']} | "
            f"{board['length']} x {board['width']} x {board['thickness']} | "
            f"{board['volume_litres']}L | "
            f"{board['construction']} | "
            f"{board['fin_system']}"
        )


if __name__ == "__main__":
    main()

    