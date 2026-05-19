import requests


URLS = [
    "https://chilli.shaperbuddy.com/api/v1/surfboardmodels",
    "https://chilli.shaperbuddy.com/api/v1/surfboardmodels?mode=fast",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


for url in URLS:

    print("")
    print("=" * 100)
    print(url)
    print("=" * 100)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=(10, 60),
    )

    print("Status:", response.status_code)
    print("Content-Type:", response.headers.get("content-type"))

    data = response.json()

    print("Rows:", len(data))

    for item in data[:80]:
        print(item.get("id_surfboardmodel"), item.get("surfboardmodel"))
