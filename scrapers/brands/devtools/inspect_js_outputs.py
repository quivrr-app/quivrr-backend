from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent

def preview_json(path: Path):
    print("\n" + "=" * 80)
    print(f"FILE: {path}")
    print(f"SIZE: {path.stat().st_size} bytes")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Could not read JSON: {exc}")
        return

    print(f"TYPE: {type(data).__name__}")

    if isinstance(data, list):
        print(f"COUNT: {len(data)}")
        if data:
            print("FIRST ITEM:")
            print(json.dumps(data[0], indent=2, ensure_ascii=False)[:3000])

    elif isinstance(data, dict):
        print(f"KEYS: {list(data.keys())}")
        print("PREVIEW:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])

def main():
    json_files = sorted(BASE_DIR.rglob("*.json"))

    if not json_files:
        print("No JSON files found under scrapers/brands")
        return

    for path in json_files:
        preview_json(path)

if __name__ == "__main__":
    main()
    