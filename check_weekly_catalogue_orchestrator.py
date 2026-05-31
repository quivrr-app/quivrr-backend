import ast
import json
from pathlib import Path


ROOT = Path.cwd()
WEEKLY = ROOT / "scrapers" / "brands" / "run_all_brand_catalogues.py"

EXPECTED = [
    "Album",
    "Channel Islands",
    "Chemistry Surfboards",
    "Chilli",
    "Christenson",
    "DHD",    "Firewire",
    "Haydenshapes",
    "JS Industries",
    "Lost",
    "Misfit Shapes",
    "Pukas",
    "Pyzel",
    "Rusty",
    "Sharp Eye",
    "Simon Anderson",
]


def load_pipelines():
    text = WEEKLY.read_text(encoding="utf-8")
    tree = ast.parse(text)

    pipelines = []

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if getattr(target, "id", None) != "PIPELINES":
                continue

            if not isinstance(node.value, ast.List):
                continue

            for item in node.value.elts:
                if not isinstance(item, ast.Dict):
                    continue

                pipeline = {}

                for key_node, value_node in zip(item.keys, item.values):
                    if not isinstance(key_node, ast.Constant):
                        continue

                    key = key_node.value

                    if key == "name" and isinstance(value_node, ast.Constant):
                        pipeline["name"] = value_node.value

                    if key == "command" and isinstance(value_node, ast.List):
                        command = []

                        for cmd in value_node.elts:
                            if isinstance(cmd, ast.Constant):
                                command.append(cmd.value)
                            elif isinstance(cmd, ast.Attribute):
                                command.append("sys.executable")
                            else:
                                command.append("<unknown>")

                        pipeline["command"] = command

                if pipeline:
                    pipelines.append(pipeline)

    return pipelines


def extract_script_path(command):
    for item in command:
        if isinstance(item, str) and item.endswith(".py"):
            return item

    return None


def find_quoted_paths(text, starts_with):
    paths = []

    for line in text.splitlines():
        if starts_with not in line or ".py" not in line:
            continue

        for quote in ['"', "'"]:
            if quote in line:
                parts = line.split(quote)

                for part in parts:
                    if part.startswith(starts_with) and part.endswith(".py"):
                        paths.append(part)

    return paths


def inspect_wrapper(path):
    if not path.exists():
        return {
            "exists": False,
            "script_runner": None,
            "script_runner_exists": False,
            "builder": None,
            "builder_exists": False,
            "importer": None,
            "importer_exists": False,
        }

    text = path.read_text(encoding="utf-8")

    runners = find_quoted_paths(text, "scripts/run_")
    script_runner = runners[0] if runners else None
    script_runner_path = ROOT / script_runner if script_runner else None

    builder = None
    importer = None

    if script_runner_path and script_runner_path.exists():
        runner_text = script_runner_path.read_text(encoding="utf-8")

        builders = find_quoted_paths(runner_text, "scrapers/brands/")
        importers = find_quoted_paths(runner_text, "scripts/import_")

        builder = builders[0] if builders else None
        importer = importers[0] if importers else None

    return {
        "exists": True,
        "script_runner": script_runner,
        "script_runner_exists": bool(script_runner_path and script_runner_path.exists()),
        "builder": builder,
        "builder_exists": bool(builder and (ROOT / builder).exists()),
        "importer": importer,
        "importer_exists": bool(importer and (ROOT / importer).exists()),
    }


def main():
    pipelines = load_pipelines()

    report = []
    configured_names = []

    print("")
    print("=" * 100)
    print("WEEKLY MANUFACTURER CATALOGUE ORCHESTRATOR CHECK")
    print("=" * 100)
    print(f"Weekly file: {WEEKLY}")
    print(f"Configured pipelines: {len(pipelines)}")
    print("")

    for pipeline in pipelines:
        name = pipeline.get("name")
        configured_names.append(name)

        command_path = extract_script_path(pipeline.get("command", []))
        wrapper_path = ROOT / command_path if command_path else None

        wrapper = inspect_wrapper(wrapper_path) if wrapper_path else {
            "exists": False,
            "script_runner": None,
            "script_runner_exists": False,
            "builder": None,
            "builder_exists": False,
            "importer": None,
            "importer_exists": False,
        }

        ok = (
            bool(command_path)
            and wrapper["exists"]
            and wrapper["script_runner_exists"]
            and wrapper["builder_exists"]
            and wrapper["importer_exists"]
        )

        row = {
            "brand": name,
            "weekly_wrapper": command_path,
            "wrapper_exists": wrapper["exists"],
            "script_runner": wrapper["script_runner"],
            "script_runner_exists": wrapper["script_runner_exists"],
            "builder": wrapper["builder"],
            "builder_exists": wrapper["builder_exists"],
            "importer": wrapper["importer"],
            "importer_exists": wrapper["importer_exists"],
            "status": "OK" if ok else "CHECK",
        }

        report.append(row)

        print(f"{row['status']:5} {name}")
        print(f"      wrapper : {row['weekly_wrapper']} ({row['wrapper_exists']})")
        print(f"      runner  : {row['script_runner']} ({row['script_runner_exists']})")
        print(f"      builder : {row['builder']} ({row['builder_exists']})")
        print(f"      importer: {row['importer']} ({row['importer_exists']})")

    missing_expected = [name for name in EXPECTED if name not in configured_names]
    extra_configured = [name for name in configured_names if name not in EXPECTED]

    print("")
    print("=" * 100)
    print("EXPECTED MANUFACTURER COVERAGE")
    print("=" * 100)
    print(f"Expected: {len(EXPECTED)}")
    print(f"Configured: {len(configured_names)}")
    print(f"Missing expected: {missing_expected}")
    print(f"Extra configured: {extra_configured}")

    output = ROOT / "scrapers" / "brands" / "output" / "weekly_catalogue_orchestrator_check.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "expected_count": len(EXPECTED),
                "configured_count": len(configured_names),
                "missing_expected": missing_expected,
                "extra_configured": extra_configured,
                "pipelines": report,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print(f"Report written: {output}")

    bad = [row for row in report if row["status"] != "OK"]

    if missing_expected or bad:
        print("")
        print("CHECK REQUIRED")
        raise SystemExit(1)

    print("")
    print("All expected weekly catalogue manufacturers are wired correctly.")


if __name__ == "__main__":
    main()
