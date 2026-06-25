from __future__ import annotations

import re


HOUSE_BRAND_ALIASES_BY_RETAILER = {
    "degree_33_surfboards": {
        "domestic": "Degree 33",
        "imported": "Degree 33",
        "sale": "Degree 33",
        "roland": "Degree 33",
        "jimmy romo": "Degree 33",
        "demo": "Degree 33",
        "discontinued": "Degree 33",
    },
    "infinity_surfboards": {
        "shred speed": "Infinity",
        "shred and speed": "Infinity",
        "island daze": "Infinity",
    },
    "walden_surfboards": {
        "st": "Walden",
        "sw": "Walden",
        "sticker junkie": "Walden",
    },
}


EXCLUDED_PRODUCT_PATTERNS = [
    ("used_board", re.compile(r"\bused\b", re.IGNORECASE)),
    ("consignment_board", re.compile(r"\bconsignment\b", re.IGNORECASE)),
    ("trade_in_board", re.compile(r"\btrade[\s-]*in\b", re.IGNORECASE)),
    ("wall_art", re.compile(r"\bwall art\b", re.IGNORECASE)),
    ("custom_deposit", re.compile(r"\bcustom deposit\b", re.IGNORECASE)),
    ("kneeboard", re.compile(r"\bkneeboard\b", re.IGNORECASE)),
]


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_key(value: object) -> str:
    text = _clean(value).lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def excluded_product_type(row: dict) -> str | None:
    text = " ".join(
        [
            _clean(row.get("retailerName")),
            _clean(row.get("brandName")),
            _clean(row.get("modelName")),
            _clean(row.get("rawProductTitle")),
        ]
    )
    for reason, pattern in EXCLUDED_PRODUCT_PATTERNS:
        if pattern.search(text):
            return reason
    return None


def _strip_leading_length(text: str) -> str:
    return re.sub(r"^\d{1,2}'\d{1,2}\"?\s*", "", text).strip()


def _strip_board_number(text: str) -> str:
    return re.sub(r"^\d{4,6}\s+", "", text).strip()


def _title_model_for_bing(title: str) -> str:
    model = _strip_leading_length(_strip_board_number(title))
    model = re.sub(r"\bboardroom collection\b", "", model, flags=re.IGNORECASE)
    return model.strip(" -#")


def _title_model_for_stewart(title: str) -> str:
    model = _strip_leading_length(title)
    model = re.sub(r"\s*\([^)]*\)", "", model)
    model = re.sub(r"\s+B#\d+\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\b(EPS|POLY|PU)\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"^USED\s+", "", model, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", model).strip(" -#\"")


def _title_model_for_infinity(title: str) -> str:
    model = _strip_leading_length(title)
    model = re.sub(r"\s{2,}", " ", model)
    return model.strip(" -#\"")


def _title_model_for_walden(title: str) -> str:
    model = re.sub(r"^Surftech\s+", "", title, flags=re.IGNORECASE)
    model = re.sub(r"^\d{4}\s+", "", model)
    model = _strip_leading_length(model)
    model = re.sub(r"\s+#?\d{4,6}\b", "", model)
    model = re.sub(r"\s+\b(TUFLITE|SOFTOP|FUSION)\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\s+\b\d{4}\b", "", model)
    return re.sub(r"\s+", " ", model).strip(" -#\"")


def _title_model_for_degree_33(title: str) -> str:
    model = _strip_leading_length(title)
    model = re.sub(r"\bSurfboard\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\bCloseout\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\bUsed\b", "", model, flags=re.IGNORECASE)
    model = re.sub(r"\([^)]*\)", "", model)
    return re.sub(r"\s+", " ", model).strip(" -#\"")


def normalise_brand_and_model_for_projection(row: dict) -> tuple[str, str, list[str]]:
    retailer_slug = _clean(row.get("retailerSlug"))
    raw_brand = _clean(row.get("brandName"))
    raw_model = _clean(row.get("modelName"))
    raw_title = _clean(row.get("rawProductTitle"))
    reasons: list[str] = []
    brand = raw_brand
    model = raw_model

    alias_map = HOUSE_BRAND_ALIASES_BY_RETAILER.get(retailer_slug, {})
    mapped_brand = alias_map.get(_clean_key(raw_brand))
    if mapped_brand:
        brand = mapped_brand
        reasons.append("brand_parsing_issue")

    if retailer_slug == "bing_surfboards":
        parsed = _title_model_for_bing(raw_title)
        if parsed and parsed != raw_model:
            model = parsed
            reasons.append("model_parsing_issue")
    elif retailer_slug == "stewart_surfboards":
        parsed = _title_model_for_stewart(raw_title)
        if parsed and parsed != raw_model:
            model = parsed
            reasons.append("model_parsing_issue")
    elif retailer_slug == "infinity_surfboards":
        parsed = _title_model_for_infinity(raw_title)
        if parsed and parsed != raw_model:
            model = parsed
            reasons.append("model_parsing_issue")
    elif retailer_slug == "walden_surfboards":
        parsed = _title_model_for_walden(raw_title)
        if parsed and parsed != raw_model:
            model = parsed
            reasons.append("model_parsing_issue")
    elif retailer_slug == "degree_33_surfboards":
        parsed = _title_model_for_degree_33(raw_title)
        if parsed and parsed != raw_model:
            model = parsed
            reasons.append("model_parsing_issue")

    return brand, model, sorted(set(reasons))
