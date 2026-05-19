from pathlib import Path


path = Path("scrapers/brands/christenson/discover_christenson_model_links.py")

text = path.read_text(encoding="utf-8")

text = text.replace(
    '"https://christensonsurfboards.com/alternative-mid",',
    '"https://christensonsurfboards.com/alternative-mids",'
)

text = text.replace(
    '"https://christensonsurfboards.com/step-ups-and-guns",',
    '"https://christensonsurfboards.com/stepups-guns",'
)

old = '''
    response = requests.get(
        category_url,
        headers=HEADERS,
        timeout=(10, 30),
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
'''

new = '''
    try:

        response = requests.get(
            category_url,
            headers=HEADERS,
            timeout=(10, 30),
        )

        response.raise_for_status()

    except Exception as exc:

        print("")
        print("FAILED CATEGORY:", category_url)
        print("ERROR:", exc)

        continue

    soup = BeautifulSoup(response.text, "html.parser")
'''

if old not in text:
    raise RuntimeError("Could not find response block")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("Patched Christenson category discovery script")
