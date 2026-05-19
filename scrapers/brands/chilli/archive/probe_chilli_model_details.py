import json
from pathlib import Path

import requests


MODELS_URL = "https://chilli.shaperbuddy.com/api/v1/surfboardmodels"
DETAIL_URL = "https://chilli.shaperbuddy.com/api/v1/surfboardmodels/{id}?lang=en"

OUTPUT_FILE = Path("scrapers/brands/chilli/output/chilli_model_detail_probe.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


models = requests.get(
    MODELS_URL,
    headers=HEADERS,
    timeout=(10, 60),
).json()

results = []

print("")
print("=" * 100)
print("CHILLI MODEL DETAIL PROBE")
print("=" * 100)

for model in models:

    model_id = model.get("id_surfboardmodel")
    model_name = model.get("surfboardmodel")

    url = DETAIL_URL.format(id=model_id)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=(10, 60),
    )

    data = response.json()

    detail = data[0] if isinstance(data, list) and data else {}

    dims = detail.get("standard_dimensions") or []

    print(f"{model_id} | {model_name} | dimensions: {len(dims)}")

    results.append({
        "id_surfboardmodel": model_id,
        "surfboardmodel": model_name,
        "detail_status": response.status_code,
        "standard_dimensions_count": len(dims),
        "sample_dimension": dims[0] if dims else None,
    })

OUTPUT_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("")
print("Saved:", OUTPUT_FILE)
