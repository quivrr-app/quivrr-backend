from __future__ import annotations


US_MANUFACTURER_SHIPPING = {
    "Christenson": {
        "sourceRegionCode": "US",
        "shippingScope": "domestic_us",
        "shippingNote": None,
    },
    "Lost": {
        "sourceRegionCode": "US",
        "shippingScope": "domestic_us",
        "shippingNote": None,
    },
    "Misfit Shapes": {
        "sourceRegionCode": "AU",
        "shippingScope": "worldwide",
        "shippingNote": (
            "In stock direct from manufacturer. This board may ship from another region, "
            "so delivery time, import duties and taxes may apply. Check confirmed retailer "
            "options below for local stock."
        ),
    },
    "Chilli": {
        "sourceRegionCode": "AU",
        "shippingScope": "worldwide",
        "shippingNote": (
            "In stock direct from manufacturer. This board may ship from another region, "
            "so delivery time, import duties and taxes may apply. Check confirmed retailer "
            "options below for local stock."
        ),
    },
    "Pukas": {
        "sourceRegionCode": "EU",
        "shippingScope": "worldwide",
        "shippingNote": (
            "In stock direct from manufacturer. This board may ship from another region, "
            "so delivery time, import duties and taxes may apply. Check confirmed retailer "
            "options below for local stock."
        ),
    },
    "Simon Anderson": {
        "sourceRegionCode": "AU",
        "shippingScope": "australia_only",
        "shippingNote": "Manufacturer direct availability is currently Australia-only.",
    },
}


def shipping_metadata_for_brand(brand_name: str | None, region_code: str | None) -> dict:
    if (region_code or "").upper() != "US":
        return {}
    return dict(US_MANUFACTURER_SHIPPING.get(brand_name or "", {}))
