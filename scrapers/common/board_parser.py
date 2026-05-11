import json
import re
from functools import lru_cache
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BRANDS_FILE = ROOT_DIR / "scrapers" / "brands" / "brands_seed.json"


BRAND_ALIASES = {
    "JS Industries": ["JS", "JS Industries"],
    "Channel Islands": ["Channel Islands", "CI"],
    "Lost": ["Lost", "Mayhem"],
    "Sharp Eye": ["Sharp Eye", "SharpEye"],
    "Chemistry Surfboards": ["Chemistry", "Chemistry Surfboards"],
    "Mick Fanning Softboards": ["Mick Fanning", "Mick Fanning Softboards"],
}


CONSTRUCTION_KEYWORDS = [
    "hyfi 3.0",
    "hyfi 2.0",
    "black sheep",
    "easy rider",
    "soft top",
    "softboard",
    "spinetek",
    "thunderbolt",
    "futureflex",
    "dark arts",
    "carbotune",
    "helium",
    "tec",
    "epoxy",
    "hyfi",
    "pu",
    "eps",
    "pe",
    "carbon",
    "fusion",
]


FIN_KEYWORDS = [
    "fcs ii",
    "fcsii",
    "single fin",
    "futures",
    "fcs",
    "twin",
    "thruster",
    "quad",
    "2+1",
]


LENGTH_REGEX = re.compile(
    r"(\d{1,2})(?:['’]|&#8217;|ft)\s*(\d{1,2}(?:\.\d+)?)?",
    re.IGNORECASE,
)

LITRES_REGEX = re.compile(
    r"(\d{1,2}\.?\d*)\s?L",
    re.IGNORECASE,
)


def clean_text(value):
    if not value:
        return ""

    value = str(value)
    value = value.replace("&#8217;", "'")
    value = value.replace("’", "'")
    value = value.replace("×", "x")
    value = value.lower()
    value = re.sub(r"\s+", " ", value)

    return value.strip()


@lru_cache(maxsize=1)
def load_known_brands():
    brands = []

    if BRANDS_FILE.exists():
        try:
            data = json.loads(BRANDS_FILE.read_text(encoding="utf-8"))

            for item in data:
                brand_name = item.get("brand_name")

                if brand_name:
                    brands.append(brand_name)

                for alias in BRAND_ALIASES.get(brand_name, []):
                    brands.append(alias)

        except Exception:
            pass

    for canonical, aliases in BRAND_ALIASES.items():
        brands.append(canonical)
        brands.extend(aliases)

    unique = sorted(set(brands), key=len, reverse=True)

    return unique


def extract_brand(title):
    title_clean = clean_text(title)

    for brand in load_known_brands():
        brand_clean = clean_text(brand)

        if re.search(rf"\b{re.escape(brand_clean)}\b", title_clean):
            return brand

    return None


def extract_length(title):
    title_clean = clean_text(title)
    match = LENGTH_REGEX.search(title_clean)

    if not match:
        return None

    feet = match.group(1)
    inches = match.group(2) or "0"

    if inches.endswith(".0"):
        inches = inches[:-2]

    return f"{feet}'{inches}"


def extract_volume(title):
    match = LITRES_REGEX.search(str(title or ""))

    if not match:
        return None

    return float(match.group(1))


def extract_construction(title):
    title_clean = clean_text(title)

    for keyword in CONSTRUCTION_KEYWORDS:
        if keyword in title_clean:
            return keyword.upper()

    return None


def extract_fin_system(title):
    title_clean = clean_text(title)

    for keyword in FIN_KEYWORDS:
        if keyword in title_clean:
            if keyword == "fcsii":
                return "FCS II"

            return keyword.upper()

    return None


def parse_board(title):
    return {
        "brand": extract_brand(title),
        "length": extract_length(title),
        "volume_litres": extract_volume(title),
        "construction": extract_construction(title),
        "fin_system": extract_fin_system(title),
    }
