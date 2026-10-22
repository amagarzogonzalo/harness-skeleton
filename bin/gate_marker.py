#!/usr/bin/env python3
"""Write and verify the evidence that the gate ran.

    python bin/gate_marker.py write
    python bin/gate_marker.py check
    python bin/gate_marker.py status

`make check` calls `write` only after every check passed. The pre-commit hook
runs `make check`, so a commit made through git always carries fresh evidence.
The commit-guard plugin calls `check` before a `git commit` and fails closed.

The marker is a guardrail, not a security boundary: anything with write access
to `artifacts/` can forge it. Its job is to catch the ordinary failure — an
agent claiming the gate passed without running it.

The worktree hash is content-based on purpose. `git status --porcelain` changes
when a file moves from unstaged to staged, so it cannot be compared across
`git add`; this can.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 1
RELATIVE_MARKER = Path("artifacts") / "gate.json"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def head(root: Path) -> str:
    try:
        return _git(root, "rev-parse", "HEAD").strip()
    except subprocess.CalledProcessError:
        return "UNBORN"


def worktree_hash(root: Path) -> str:
    """Hash the content the next commit would contain, independent of index state.

    Includes tracked files (even when deleted, represented as `<missing>`) and
    untracked non-ignored files. Excluded by construction: `.git/`, ignored
    files such as `artifacts/`, and anything the project chose to ignore.
    """
    raw = subprocess.run(
        ["git", "ls-files", "-z", "-c", "-o", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    paths = sorted(p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p)

    digest = hashlib.sha256()
    for rel in paths:
        path = root / rel
        digest.update(rel.encode("utf-8", "surrogateescape") + b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<missing>")
        digest.update(b"\0")
    return digest.hexdigest()


def write(root: Path) -> dict:
    marker_path = root / RELATIVE_MARKER
    marker = {
        "schema": SCHEMA,
        "ok": True,
        "command": "make check",
        "head": head(root),
        "worktree": worktree_hash(root),
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    return marker


def check(root: Path) -> list[str]:
    marker_path = root / RELATIVE_MARKER
    if not marker_path.exists():
        return ["no gate marker: run `make check` first"]

    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"gate marker is not valid JSON: {exc}"]

    problems: list[str] = []
    if marker.get("schema") != SCHEMA:
        problems.append("gate marker schema changed; run `make check` again")
    if marker.get("ok") is not True:
        problems.append("the last gate run did not pass")

    current_head = head(root)
    if marker.get("head") != current_head:
        problems.append(f"HEAD moved since the gate ran ({marker.get('head')} -> {current_head})")

    if marker.get("worktree") != worktree_hash(root):
        problems.append("the working tree changed since the gate ran")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root (default: this checkout)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("write", help="record a successful gate run")
    sub.add_parser("check", help="exit non-zero when the evidence is stale")
    sub.add_parser("status", help="print the marker and its verdict")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()

    if args.command == "write":
        marker = write(root)
        print(f"gate: wrote {root / RELATIVE_MARKER} ({marker['head'][:12]})")
        return 0

    problems = check(root)

    if args.command == "status":
        print(f"root: {root}")
        marker_path = root / RELATIVE_MARKER
        print(marker_path.read_text(encoding="utf-8") if marker_path.exists() else "no marker")
        print("verdict: " + ("ok" if not problems else "stale"))

    if problems:
        for problem in problems:
            print(f"gate: {problem}", file=sys.stderr)
        return 1

    print("gate: evidence is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
