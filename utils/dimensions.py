from decimal import Decimal, InvalidOperation
import re


DEFAULT_WIDTH_TOLERANCE = Decimal("0.15")
DEFAULT_THICKNESS_TOLERANCE = Decimal("0.08")
DEFAULT_VOLUME_TOLERANCE = Decimal("0.75")

FRACTION_MAP = {
    "1/16": Decimal("0.0625"),
    "1/8": Decimal("0.125"),
    "3/16": Decimal("0.1875"),
    "1/4": Decimal("0.25"),
    "5/16": Decimal("0.3125"),
    "3/8": Decimal("0.375"),
    "7/16": Decimal("0.4375"),
    "1/2": Decimal("0.5"),
    "9/16": Decimal("0.5625"),
    "5/8": Decimal("0.625"),
    "11/16": Decimal("0.6875"),
    "3/4": Decimal("0.75"),
    "13/16": Decimal("0.8125"),
    "7/8": Decimal("0.875"),
    "15/16": Decimal("0.9375"),
}


def clean_dimension_text(value):
    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    value = (
        value.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("×", "x")
    )
    return re.sub(r"\s+", " ", value).strip() or None


def decimal_measurement(value):
    value = clean_dimension_text(value)
    if not value:
        return None

    value = value.replace(",", ".").replace('"', "")
    value = re.sub(r"\s*(?:in(?:ches?)?|litres?|liters?|l)\s*$", "", value, flags=re.I)
    try:
        return Decimal(value)
    except InvalidOperation:
        pass

    total = Decimal("0")
    for part in value.split(" "):
        if part in FRACTION_MAP:
            total += FRACTION_MAP[part]
            continue
        try:
            total += Decimal(part)
        except InvalidOperation:
            return None
    return total


def dimension_to_decimal(value):
    parsed = decimal_measurement(value)
    return float(parsed) if parsed is not None else None


def volume_to_decimal(value):
    return decimal_measurement(value)


def length_to_inches(value):
    """Parse common surfboard length formats into an exact inch count."""
    value = clean_dimension_text(value)
    if not value:
        return None

    patterns = (
        r"(?<!\d)(?P<feet>\d+)\s*(?:'|ft|feet)\s*(?P<inches>\d{1,2})?\s*(?:in|\")?",
        # A small number of feeds use 5\"11 for a feet/inches length.
        r"(?<!\d)(?P<feet>\d+)\s*\"\s*(?P<inches>\d{1,2})(?!\d)",
    )
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.I)
        if not match:
            continue
        feet = int(match.group("feet"))
        inches = int(match.group("inches") or 0)
        if inches >= 12:
            return None
        return feet * 12 + inches
    return None


def dimensions_from_title(value):
    """Extract length, width, thickness and volume from a listing title."""
    value = clean_dimension_text(value)
    if not value:
        return {}
    measurement = r"\d+(?:[\.,]\d+)?(?:\s+\d+\s*/\s*\d+)?"
    match = re.search(
        rf"(?P<length>\d+\s*(?:'|ft)\s*\d{{1,2}}\s*\"?)\s*[xX×]\s*"
        rf"(?P<width>{measurement})\s*\"?\s*[xX×]\s*"
        rf"(?P<thickness>{measurement})\s*\"?"
        rf"(?:\s*[xX×-]\s*(?P<volume>\d+(?:[\.,]\d+)?)\s*[lL])?",
        value,
        flags=re.I,
    )
    if not match:
        return {}
    return {
        "length": match.group("length"),
        "width": match.group("width"),
        "thickness": match.group("thickness"),
        "volume": match.group("volume"),
    }


def measurements_within(left, right, tolerance):
    left_decimal = decimal_measurement(left)
    right_decimal = decimal_measurement(right)
    if left_decimal is None or right_decimal is None:
        return False
    return abs(left_decimal - right_decimal) <= Decimal(str(tolerance))


def dimensions_match(left, right, tolerance=0.015):
    return measurements_within(left, right, tolerance)


def equivalent_board_dimensions(
    retailer,
    canonical,
    *,
    width_tolerance=DEFAULT_WIDTH_TOLERANCE,
    thickness_tolerance=DEFAULT_THICKNESS_TOLERANCE,
    volume_tolerance=DEFAULT_VOLUME_TOLERANCE,
):
    """Compare complete retailer dimensions to a canonical board size."""
    if length_to_inches(retailer.get("length")) != length_to_inches(canonical.get("length")):
        return False
    comparisons = (
        ("width", width_tolerance),
        ("thickness", thickness_tolerance),
        ("volume", volume_tolerance),
    )
    return all(
        retailer.get(field) not in (None, "")
        and canonical.get(field) not in (None, "")
        and measurements_within(retailer[field], canonical[field], tolerance)
        for field, tolerance in comparisons
    )
