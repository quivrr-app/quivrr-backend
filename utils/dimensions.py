from decimal import Decimal, InvalidOperation
import re


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
        .replace('"', "")
    )

    value = re.sub(r"\s+", " ", value).strip()

    return value or None


def dimension_to_decimal(value):
    value = clean_dimension_text(value)

    if not value:
        return None

    try:
        parsed = Decimal(value)
        return float(parsed)
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

    return float(total)


def dimensions_match(left, right, tolerance=0.015):
    left_decimal = dimension_to_decimal(left)
    right_decimal = dimension_to_decimal(right)

    if left_decimal is None or right_decimal is None:
        return False

    return abs(left_decimal - right_decimal) <= tolerance
