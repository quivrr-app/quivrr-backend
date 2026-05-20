from pathlib import Path

path = Path("scrapers/brands/run_all_brand_catalogues.py")
text = path.read_text(encoding="utf-8")

print("")
print("=" * 100)
print("LOCAL WEEKLY RUNNER BRANDS")
print("=" * 100)
print("Runner:", path)

for line in text.splitlines():
    stripped = line.strip()

    if stripped.startswith('"name":'):
        brand = stripped.split(":", 1)[1].strip().strip('",')
        print("-", brand)
