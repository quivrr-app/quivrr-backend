from pathlib import Path

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")
text = path.read_text(encoding="utf-8")

old = r'''    pattern = (
        r"(?P<length>\d+'\s*\d{1,2})"
        r"(?:\s*HV)?"
        r"\s*x\s*"
        r"(?P<width>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)"
        r"\s*x\s*"
        r"(?P<thickness>\d+(?:\.\d+)?(?:\s+\d+/\d+)?)"
        r"\s*x\s*"
        r"(?P<volume>\d+(?:\.\d+)?)\s*L"
    )
'''

new = r'''    pattern = (
        r"(?P<length>\d+'\s*\d{1,2})"
        r'["”″]?'
        r"(?:\s*HV)?"
        r"\s*[xX]\s*"
        r"(?P<width>\d+(?:\.\d+)?)"
        r"\s*[xX]\s*"
        r"(?P<thickness>\d+(?:\.\d+)?)"
        r"\s*[xX]\s*"
        r"(?P<volume>\d+(?:\.\d+)?)\s*L"
    )
'''

if old not in text:
    raise RuntimeError("Could not find dimension regex block")

text = text.replace(old, new)

insert_after = '''def fetch_products():
'''

fallback_function = r'''

def extract_dimensions_from_html(product_url):
    response = requests.get(
        product_url,
        headers=HEADERS,
        timeout=(10, 30),
    )

    html = clean(response.text)

    matches = re.findall(
        r"(\d+'\s*\d{1,2}[\"”″]?\s*[xX]\s*\d+(?:\.\d+)?\s*[xX]\s*\d+(?:\.\d+)?\s*[xX]\s*\d+(?:\.\d+)?\s*L)",
        html,
        flags=re.IGNORECASE,
    )

    return sorted(set(matches))


'''

if "def extract_dimensions_from_html" not in text:
    text = text.replace(insert_after, fallback_function + insert_after)

old_block = r'''            if not variant_title or variant_title.lower() == "default title":
                failures.append({
                    "model": model_name,
                    "title": title,
                    "variant_title": variant_title,
                    "reason": "default title variant has no dimensions",
                    "product_url": product_url,
                })
                continue
'''

new_block = r'''            if not variant_title or variant_title.lower() == "default title":

                fallback_dimensions = extract_dimensions_from_html(product_url)

                if not fallback_dimensions:
                    failures.append({
                        "model": model_name,
                        "title": title,
                        "variant_title": variant_title,
                        "reason": "default title variant has no dimensions",
                        "product_url": product_url,
                    })
                    continue

                for fallback_variant in fallback_dimensions:

                    dimensions = parse_dimensions(fallback_variant)

                    if not dimensions["length"]:
                        continue

                    board_category = "Youth Shortboard" if "YTH" in title.upper() or "YOUTH" in title.upper() else "Shortboard"

                    if dimensions.get("is_hv"):
                        board_category = "High Volume Shortboard"

                    rows.append({
                        "brand": BRAND,
                        "model_name": model_name,
                        "model_family": model_name,
                        "board_category": board_category,
                        "description": description,
                        "official_product_url": product_url,
                        "official_image_url": image_url,
                        "recommended_wave_range": None,
                        "recommended_surfer_weight": None,
                        "length_feet_inches": dimensions["length"],
                        "width": dimensions["width"],
                        "thickness": dimensions["thickness"],
                        "volume_litres": float(dimensions["volume_litres"]) if dimensions["volume_litres"] is not None else None,
                        "construction": construction,
                        "fin_setup": detect_fin_setup(fallback_variant),
                        "tail_shape": None,
                        "source_product_title": title,
                        "source_variant_title": fallback_variant,
                        "source": BASE_URL,
                    })

                continue
'''

if old_block not in text:
    raise RuntimeError("Could not find default title block")

text = text.replace(old_block, new_block)

path.write_text(text, encoding="utf-8")

print("Patched Sharp Eye HTML dimension fallback")
