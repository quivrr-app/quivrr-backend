from pathlib import Path


path = Path("scrapers/brands/album/build_album_master_catalogue.py")

text = path.read_text(encoding="utf-8")

old = '''
    return sorted(urls)
'''

new = '''
    canonicalised = {}

    for url in urls:

        slug = url.split("/collections/")[-1]

        canonical_slug = slug
        canonical_slug = canonical_slug.replace("-concept", "")
        canonical_slug = canonical_slug.replace("-1", "")

        existing = canonicalised.get(canonical_slug)

        if existing is None:
            canonicalised[canonical_slug] = url
            continue

        existing_score = 0
        new_score = 0

        if "-concept" not in existing:
            existing_score += 10

        if "-1" not in existing:
            existing_score += 5

        if "-concept" not in url:
            new_score += 10

        if "-1" not in url:
            new_score += 5

        if new_score > existing_score:
            canonicalised[canonical_slug] = url

    return sorted(canonicalised.values())
'''

if old not in text:
    raise RuntimeError("Could not find return sorted(urls)")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("Patched Album canonical URL selection")
