import re

from utils.dimensions import (
    DEFAULT_VOLUME_TOLERANCE,
    dimensions_from_title,
    equivalent_board_dimensions,
    length_to_inches,
    measurements_within,
)


CONSTRUCTION_ALIASES = {
    "standard": "",
    "rt": "",
    "carbon tune": "carbotune",
    "hyfi 3": "hyfi",
    "hyfi 3 0": "hyfi",
    "i bolic": "ibolic",
    "i bolic 2 0": "ibolic",
    "pu stringer": "pu",
    "polyester": "pu",
    "spine tek": "spinetek",
    "ect carbon": "ectcarbon",
    "future flex": "futureflex",
    "black sheep": "blacksheep",
    "c1 carbon": "c1carbon",
    "e3 lite": "e3lite",
}

KNOWN_CONSTRUCTION_TOKENS = {
    "carbotune": ("carbotune", "carbon tune"),
    "hyfi": ("hyfi", "hyfi 3", "hyfi 3.0"),
    "ibolic": ("ibolic", "i-bolic", "i bolic"),
    "pu": (" pu ", "polyester", "pu stringer"),
    "pe": (" pe ",),
    "eps": (" eps ",),
    "spinetek": ("spine-tek", "spine tek", "spinetek"),
    "ectcarbon": ("ect-carbon", "ect carbon"),
    "futureflex": ("futureflex", "future flex", "ff"),
    "helium": ("helium",),
    "blacksheep": ("black sheep",),
    "lightspeed": ("light speed", "lightspeed"),
    "c1carbon": ("c1carbon", "c1 carbon"),
    "e3lite": ("e3lite", "e3 lite"),
}


def text_key(value):
    value = str(value or "").lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def construction_key(value):
    key = text_key(value)
    return CONSTRUCTION_ALIASES.get(key, key)


def construction_from_title(title):
    padded = f" {text_key(title)} "
    found = set()
    for canonical, tokens in KNOWN_CONSTRUCTION_TOKENS.items():
        if any(f" {text_key(token)} " in padded for token in tokens):
            found.add(canonical)
    return found


def construction_compatible(retailer, canonical):
    canonical_key = construction_key(canonical.get("construction"))
    retailer_key = construction_key(retailer.get("construction"))
    title_constructions = construction_from_title(retailer.get("title"))
    if not canonical_key:
        return True, "canonical_construction_unknown"
    if title_constructions:
        return (
            canonical_key in title_constructions,
            "title_construction_match" if canonical_key in title_constructions else "title_construction_mismatch",
        )
    if retailer_key:
        return (
            retailer_key == canonical_key,
            "construction_match" if retailer_key == canonical_key else "construction_mismatch",
        )

    # Unknown construction is not evidence of a mismatch. Explicit fields or
    # recognised title tokens above remain authoritative and conservative.
    return True, "construction_unknown"


def classify_retailer_exact(
    retailer,
    canonical,
    *,
    brand_matches,
    model_matches,
    strong_model_title=False,
):
    """Apply conservative exact-match policy after regional SQL filtering."""
    if not brand_matches:
        return False, "brand_mismatch"
    if not model_matches:
        return False, "model_mismatch"

    parsed_title_dimensions = dimensions_from_title(retailer.get("title"))
    retailer = {
        **retailer,
        "length": retailer.get("length") or parsed_title_dimensions.get("length"),
        "width": retailer.get("width") or parsed_title_dimensions.get("width"),
        "thickness": retailer.get("thickness") or parsed_title_dimensions.get("thickness"),
        "volume": retailer.get("volume") or parsed_title_dimensions.get("volume"),
    }
    retailer_length = retailer.get("length") or retailer.get("title")
    if length_to_inches(retailer_length) != length_to_inches(canonical.get("length")):
        return False, "length_mismatch"

    construction_ok, construction_reason = construction_compatible(retailer, canonical)
    if not construction_ok:
        return False, construction_reason

    retailer_size_id = retailer.get("boardSizeId")
    canonical_size_id = canonical.get("boardSizeId")
    if retailer_size_id is not None and retailer_size_id == canonical_size_id:
        return True, "board_size_id"

    if equivalent_board_dimensions(retailer, canonical):
        return True, "equivalent_dimensions"

    width_missing = retailer.get("width") in (None, "")
    thickness_missing = retailer.get("thickness") in (None, "")
    if (
        width_missing
        and thickness_missing
        and strong_model_title
        and retailer.get("volume") not in (None, "")
        and canonical.get("volume") not in (None, "")
        and measurements_within(
            retailer["volume"],
            canonical["volume"],
            DEFAULT_VOLUME_TOLERANCE,
        )
    ):
        return True, "length_volume_strong_model"

    if retailer.get("volume") in (None, ""):
        return False, "missing_volume"
    if width_missing or thickness_missing:
        return False, "missing_width_or_thickness"
    return False, "dimensions_outside_tolerance"
