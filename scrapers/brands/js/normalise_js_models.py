from urllib.parse import urlparse


EXCLUDED_TERMS = [
    "gift card",
]

MODEL_CLASSIFIERS = {
    "softboard": ["softboard"],
    "youth": ["youth"],
    "easy_rider": ["easy rider"],
}


def clean_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def classify_model(model_name: str, url: str) -> dict:
    value = f"{model_name} {url}".lower()

    return {
        "is_softboard": any(term in value for term in MODEL_CLASSIFIERS["softboard"]),
        "is_youth": any(term in value for term in MODEL_CLASSIFIERS["youth"]),
        "is_easy_rider": any(term in value for term in MODEL_CLASSIFIERS["easy_rider"]),
    }


def normalise_js_model(raw_model: dict) -> dict | None:
    model_name = raw_model["model_name"].strip()
    url = clean_url(raw_model["url"])

    if any(term in model_name.lower() for term in EXCLUDED_TERMS):
        return None

    classifiers = classify_model(model_name, url)

    canonical_name = model_name
    canonical_name = canonical_name.replace(" Easy Rider", "")
    canonical_name = canonical_name.replace(" Youth", "")
    canonical_name = canonical_name.replace(" (Tier 1 & 2)", "")
    canonical_name = canonical_name.replace(" (Tier 3)", "")
    canonical_name = canonical_name.strip()

    return {
        "brand_name": "JS Industries",
        "model_name": canonical_name,
        "raw_model_name": model_name,
        "official_product_url": url,
        "is_softboard": classifiers["is_softboard"],
        "is_youth": classifiers["is_youth"],
        "is_easy_rider": classifiers["is_easy_rider"],
    }


def normalise_js_models(raw_models: list[dict]) -> list[dict]:
    output = {}
    for raw_model in raw_models:
        normalised = normalise_js_model(raw_model)

        if normalised is None:
            continue

        key = (
            normalised["model_name"].lower(),
            normalised["official_product_url"].lower(),
            normalised["is_softboard"],
            normalised["is_youth"],
            normalised["is_easy_rider"],
        )

        output[key] = normalised

    return list(output.values())