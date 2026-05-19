from pathlib import Path

path = Path("scrapers/brands/sharpeye/build_sharpeye_master_catalogue.py")

lines = path.read_text(encoding="utf-8").splitlines()

print("")
print("=" * 100)
print("DEFAULT TITLE BLOCK")
print("=" * 100)

for index, line in enumerate(lines, start=1):

    if 'default title' in line.lower():

        start = max(1, index - 15)
        end = min(len(lines), index + 35)

        for line_number in range(start, end + 1):
            print(f"{line_number}: {lines[line_number - 1]}")

        break

print("")
print("=" * 100)
print("parse_dimensions FUNCTION")
print("=" * 100)

inside = False

for index, line in enumerate(lines, start=1):

    if line.startswith("def parse_dimensions"):
        inside = True

    if inside:
        print(f"{index}: {line}")

    if inside and line.startswith("def ") and not line.startswith("def parse_dimensions"):
        break
