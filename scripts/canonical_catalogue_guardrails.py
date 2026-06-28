from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REJECTED_AUDIT_PATH = Path("scripts/output/canonical_rejected_products.json")

HARD_NEGATIVE_TERMS = [
    "art",
    "book",
    "ceramic",
    "event",
    "gift card",
    "jewellery",
    "jewelry",
    "poster",
    "pottery",
    "print",
    "sticker",
    "vase",
]
SOFT_NEGATIVE_TERMS = [
    "accessory",
    "apparel",
    "bag",
    "beanie",
    "cap",
    "fin",
    "fins",
    "hat",
    "hoodie",
    "leash",
    "merch",
    "shirt",
    "sunscreen",
    "tee",
    "towel",
    "traction",
    "wax",
]
POSITIVE_TERMS = [
    "surfboard",
    "surf board",
    "shortboard",
    "longboard",
    "midlength",
    "mid length",
    "mid-length",
    "fish",
    "twin fin",
    "step up",
    "gun",
    "groveler",
    "groveller",
    "single fin",
    "performance board",
    "board models",
    "step-up",
    "glider",
    "thruster",
    "quad",
    "keel",
    "rocker",
    "concave",
    "rail",
    "tail",
]
URL_POSITIVE_TERMS = [
    "/surfboards",
    "/boards",
    "/board-models",
]
DIMENSION_RE = re.compile(
    r"\b([4-9]|1[0-1])\s*(?:'|’|ft)\s*\d{1,2}(?:\s*(?:\"|''))?"
    r"\s*x\s*\d{1,2}(?:\s+\d/\d|(?:\.\d+)?)?"
    r"\s*x\s*\d(?:\s+\d/\d|(?:\.\d+)?)?",
    re.I,
)
LENGTH_ONLY_RE = re.compile(r"\b([4-9]|1[0-1])\s*(?:'|’|ft)\s*\d{1,2}\b", re.I)
VOLUME_RE = re.compile(r"\b\d{1,2}(?:\.\d+)?\s*l(?:iters|itres)?\b", re.I)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _contains_term(text: str, terms: list[str]) -> str:
    lowered = clean(text).lower()
    for term in terms:
        pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
        if re.search(pattern, lowered):
            return term
    return ""


def _has_dimension_fields(length: Any, width: Any, thickness: Any, volume_litres: Any) -> bool:
    return bool(clean(length) and (clean(width) or clean(thickness) or clean(volume_litres)))


def _has_dimension_context(*values: Any) -> bool:
    text = " ".join(clean(value) for value in values if clean(value))
    return bool(DIMENSION_RE.search(text) or (LENGTH_ONLY_RE.search(text) and VOLUME_RE.search(text)))


def assess_catalogue_candidate(
    *,
    brand: str,
    title: Any,
    source_url: Any,
    board_category: Any = None,
    detected_product_type: Any = None,
    source_variant_title: Any = None,
    description: Any = None,
    length: Any = None,
    width: Any = None,
    thickness: Any = None,
    volume_litres: Any = None,
    extra_context: Any = None,
) -> dict[str, Any]:
    title_text = clean(title)
    category_text = clean(board_category)
    product_type_text = clean(detected_product_type)
    source_url_text = clean(source_url)
    description_text = clean(description)
    variant_text = clean(source_variant_title)
    extra_text = clean(extra_context)
    combined_text = " ".join(
        value
        for value in [
            title_text,
            category_text,
            product_type_text,
            source_url_text,
            description_text,
            variant_text,
            extra_text,
        ]
        if value
    )

    positive_term = _contains_term(" ".join([category_text, product_type_text, description_text, extra_text]), POSITIVE_TERMS)
    hard_negative_term = _contains_term(combined_text, HARD_NEGATIVE_TERMS)
    if hard_negative_term:
        return {
            "accepted": False,
            "reason": f"negative_term:{hard_negative_term}",
            "detectedCategory": category_text or None,
            "detectedProductType": product_type_text or None,
        }

    has_dimensions = _has_dimension_fields(length, width, thickness, volume_litres)
    has_dimension_context = _has_dimension_context(
        variant_text,
        description_text,
        extra_text,
        title_text,
    )
    positive_url_term = _contains_term(source_url_text, URL_POSITIVE_TERMS)
    soft_negative_term = _contains_term(combined_text, SOFT_NEGATIVE_TERMS)
    if soft_negative_term in {"fin", "fins"} and (positive_term or has_dimensions or has_dimension_context):
        soft_negative_term = ""

    if has_dimensions or has_dimension_context:
        return {
            "accepted": True,
            "reason": "dimension_signal",
            "detectedCategory": category_text or None,
            "detectedProductType": product_type_text or None,
        }

    if positive_term or positive_url_term:
        return {
            "accepted": True,
            "reason": f"context_signal:{positive_term or positive_url_term}",
            "detectedCategory": category_text or None,
            "detectedProductType": product_type_text or None,
        }

    if soft_negative_term and not positive_term and not positive_url_term:
        return {
            "accepted": False,
            "reason": f"negative_term:{soft_negative_term}",
            "detectedCategory": category_text or None,
            "detectedProductType": product_type_text or None,
        }

    return {
        "accepted": False,
        "reason": "missing_surfboard_evidence",
        "detectedCategory": category_text or None,
        "detectedProductType": product_type_text or None,
    }


def build_rejection_entry(
    *,
    brand: str,
    title: Any,
    source_url: Any,
    reason: str,
    detected_category: Any = None,
    detected_product_type: Any = None,
) -> dict[str, Any]:
    return {
        "brand": clean(brand),
        "title": clean(title),
        "sourceUrl": clean(source_url),
        "reason": clean(reason),
        "detectedCategory": clean(detected_category) or None,
        "detectedProductType": clean(detected_product_type) or None,
        "rejectedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def append_rejected_products_audit(entries: list[dict[str, Any]], path: Path | None = None) -> None:
    if not entries:
        return
    audit_path = path or REJECTED_AUDIT_PATH
    existing: list[dict[str, Any]] = []
    if audit_path.exists():
        try:
            existing = json.loads(audit_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for item in existing + entries:
        key = (
            clean(item.get("brand")).lower(),
            clean(item.get("title")).lower(),
            clean(item.get("sourceUrl")).lower(),
            clean(item.get("reason")).lower(),
        )
        merged[key] = item

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps(list(merged.values()), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def filter_catalogue_rows(
    brand: str,
    rows: list[dict[str, Any]],
    *,
    extra_context_field: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        assessment = assess_catalogue_candidate(
            brand=brand,
            title=row.get("model_name") or row.get("model") or row.get("source_product_title"),
            source_url=row.get("official_product_url") or row.get("source"),
            board_category=row.get("board_category"),
            detected_product_type=row.get("source_product_type") or row.get("detected_product_type"),
            source_variant_title=row.get("source_variant_title"),
            description=row.get("description"),
            length=row.get("length_feet_inches") or row.get("length"),
            width=row.get("width"),
            thickness=row.get("thickness"),
            volume_litres=row.get("volume_litres"),
            extra_context=row.get(extra_context_field) if extra_context_field else None,
        )
        if assessment["accepted"]:
            accepted.append(row)
            continue
        rejected.append(
            build_rejection_entry(
                brand=brand,
                title=row.get("model_name") or row.get("model") or row.get("source_product_title"),
                source_url=row.get("official_product_url") or row.get("source"),
                reason=assessment["reason"],
                detected_category=assessment["detectedCategory"],
                detected_product_type=assessment["detectedProductType"],
            )
        )
    return accepted, rejected
