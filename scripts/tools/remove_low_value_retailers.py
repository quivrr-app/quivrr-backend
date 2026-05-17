import json
from pathlib import Path

path = Path("scrapers/retailers/active_scrape_targets.json")

remove_names = {
    "slimes boardstore",
    "surf dive n ski",
}

targets = json.loads(path.read_text(encoding="utf-8"))

kept = []
removed = []

for target in targets:
    name = str(target.get("primary_name", "")).strip()
    if name.lower() in remove_names:
        removed.append(name)
    else:
        kept.append(target)

path.write_text(
    json.dumps(kept, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print()
print("Removed targets:")
for name in removed:
    print(" -", name)

print()
print("Remaining targets:", len(kept))
