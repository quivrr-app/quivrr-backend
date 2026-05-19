from scrapers.brands.sharpeye.build_sharpeye_master_catalogue import extract_dimensions_from_html

url = "https://sharpeyesurfboards.com/products/inferno-73"

rows = extract_dimensions_from_html(url)

print("Rows found:", len(rows))

for row in rows[:20]:
    print(row)
