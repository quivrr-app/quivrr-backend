from pathlib import Path
import json
import re


INPUT_FILE = Path("scrapers/products/output/shopify/js_industries.json")

CANONICAL_MODELS_FILE = Path(
    "scrapers/brands/js_canonical_models.json"
)

OUTPUT_DIR = Path("scrapers/brands/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "js_master_catalogue.json"


def load_canonical_models():
    return json.loads(
        CANONICAL_MODELS_FILE.read_text(
            encoding="utf-8"
        )
    )


def normalise_text(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def is_real_board(item):
    title = normalise_text(
        item.get("title", "")
    )

    if "Custom Order" in title:
        return False

    has_volume = re.search(
        r"\d+\.\d+L",
        title
    )

    has_length = re.search(
        r"\d{1,2}'\d{1,2}",
        title
    )

    return bool(
        has_volume
        and has_length
    )


def clean_dimension(value):
    if not value:
        return None

    value = str(value).replace('"', "")

    return normalise_text(value)


def normalise_construction(value):
    if not value:
        return None

    value = normalise_text(value)

    if value.lower() == "carbotune":
        return "CarboTune"

    if value.upper() == "PU":
        return "PU"

    return value


def find_canonical_model(
    raw_title,
    canonical_models
):
    raw_lower = raw_title.lower()

    matches = []

    for model in canonical_models:
        if model.lower() in raw_lower:
            matches.append(model)

    if not matches:
        return None

    matches.sort(
        key=len,
        reverse=True
    )

    return matches[0]


def parse_board(
    item,
    canonical_models
):
    title = normalise_text(
        item.get("title", "")
    )

    model = find_canonical_model(
        title,
        canonical_models
    )

    if not model:
        return None

    dims_match = re.search(
        r"(\d{1,2}'\d{1,2}\"?)\s*[xX]\s*"
        r"(\d+(?:\s+\d+/\d+)?(?:\.\d+)?\"?)\s*[xX]\s*"
        r"(\d+(?:\s+\d+/\d+)?(?:\.\d+)?\"?)\s*-",
        title,
        re.IGNORECASE
    )

    volume_match = re.search(
        r"(\d+\.\d+)L",
        title
    )

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
        "raw_title": title,
        "length": (
            clean_dimension(dims_match.group(1))
            if dims_match
            else None
        ),
        "width": (
            clean_dimension(dims_match.group(2))
            if dims_match
            else None
        ),
        "thickness": (
            clean_dimension(dims_match.group(3))
            if dims_match
            else None
        ),
        "volume_litres": (
            float(volume_match.group(1))
            if volume_match
            else None
        ),
        "construction": normalise_construction(
            construction_match.group(1)
            if construction_match
            else None
        ),
        "fin_system": (
            fin_match.group(1)
            if fin_match
            else None
        ),
        "tail_shape": (
            tail_match.group(1)
            if tail_match
            else None
        ),
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
        board.get("tail_shape") or "",
    ])


def main():
    canonical_models = load_canonical_models()

    raw = json.loads(
        INPUT_FILE.read_text(
            encoding="utf-8"
        )
    )

    boards = []
    skipped = 0

    for item in raw:
        if not is_real_board(item):
            skipped += 1
            continue

        parsed = parse_board(
            item,
            canonical_models
        )

        if not parsed:
            skipped += 1
            continue

        if (
            not parsed["length"]
            or not parsed["volume_litres"]
            or not parsed["construction"]
        ):
            skipped += 1
            continue

        images = item.get("images") or []

        parsed["brand"] = "JS Industries"
        parsed["price"] = item.get("price")
        parsed["available"] = item.get("available")
        parsed["product_url"] = item.get("product_url")
        parsed["image_url"] = (
            images[0]
            if images
            else None
        )

        boards.append(parsed)

    deduped = {}

    for board in boards:
        deduped[
            variant_key(board)
        ] = board

    final_catalogue = sorted(
        deduped.values(),
        key=lambda x: (
            x["model"],
            x["construction"] or "",
            x["length"] or "",
            x["volume_litres"] or 0
        )
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            final_catalogue,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("\nJS catalogue built successfully")
    print(f"Raw products: {len(raw)}")
    print(f"Parsed boards: {len(boards)}")
    print(f"Canonical variants: {len(final_catalogue)}")
    print(f"Skipped rows: {skipped}")

    print("\nModels in catalogue:\n")

    models = sorted(
        set(
            board["model"]
            for board in final_catalogue
        )
    )

    for model in models:
        print(f"- {model}")


if __name__ == "__main__":
    main()