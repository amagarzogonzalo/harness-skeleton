from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tracked_shebanged_scripts():
    result = subprocess.run(
        ["git", "ls-files", "-s"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        meta, _, path = line.partition("\t")
        if not path:
            continue
        mode = meta.split()[0]
        if not path.endswith((".py", ".sh")) and path != ".githooks/pre-commit":
            continue
        candidate = ROOT / path
        if candidate.is_file() and candidate.read_bytes().startswith(b"#!"):
            yield mode, path


def test_shebanged_scripts_are_executable():
    offenders = [path for mode, path in tracked_shebanged_scripts() if mode != "100755"]
    assert not offenders, "mark executable with `git update-index --chmod=+x`: " + ", ".join(
        offenders
    )
