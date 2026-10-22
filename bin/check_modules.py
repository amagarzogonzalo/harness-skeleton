#!/usr/bin/env python3
"""Run the check scripts of the modules enabled for this project.

Activation is explicit. A stack marker alone is not enough: the harness's own
`pyproject.toml` must not silently opt the repository into the Python module's
security tools. `bin/modules.py enable` writes `modules/.enabled.json`, and only
the modules listed there are run.

An enabled module with no declared check is legal (agents and skills only). An
enabled module whose declared check or manifest is missing is a failure, not a
silent pass: the gate must not claim to have checked something it did not.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path("modules") / ".enabled.json"


def enabled(root: Path) -> list[dict]:
    path = root / STATE
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    modules = data.get("modules", {})
    return [modules[name] for name in sorted(modules)]


def main(argv: list[str] | None = None) -> int:
    root = Path(argv[0]).resolve() if argv else ROOT
    modules = enabled(root)
    if not modules:
        print("no modules enabled (core only)")
        return 0

    shell = shutil.which("bash") or shutil.which("sh")
    if not shell:
        print("FAIL: modules are enabled but neither bash nor sh is on PATH", file=sys.stderr)
        return 1

    failed: list[str] = []
    for module in modules:
        name = module["name"]
        base = root / "modules" / name
        manifest_path = base / "module.toml"

        if not manifest_path.is_file():
            print(f"FAIL {name}: module.toml is missing", file=sys.stderr)
            failed.append(name)
            continue

        declared = tomllib.loads(manifest_path.read_text(encoding="utf-8")).get("check", "")
        if not declared:
            print(f"skip {name}: no check declared (agents and skills only)")
            continue

        script = base / declared
        if not script.is_file():
            print(
                f"FAIL {name}: declared check is missing ({script.relative_to(root).as_posix()})",
                file=sys.stderr,
            )
            failed.append(name)
            continue

        print(f"\n== module: {name} ==")
        result = subprocess.run([shell, str(script)], cwd=root, check=False)
        if result.returncode != 0:
            failed.append(name)

    if failed:
        print(f"\nFAIL: module checks failed: {', '.join(failed)}", file=sys.stderr)
        return 1

    print("\nmodules: green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
