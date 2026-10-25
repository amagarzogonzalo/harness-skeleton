#!/usr/bin/env python3
"""Offline integrity check for the vendored deep-research skill.

This runs only when the module is enabled. It verifies the source/version
record, the SHA-256 manifest, the installed copy, and the client's ``--version``
and ``--help`` commands. It never touches the network and never reads ``.env``.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
ROOT = MODULE_DIR.parents[1]
SKILL_NAME = "deep-research"
SKILL_DIR = MODULE_DIR / "skills" / SKILL_NAME
INSTALLED_DIR = ROOT / ".opencode" / "skills" / SKILL_NAME


def sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of one file.

    Args:
        path: File to hash.

    Returns:
        str: Hex digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files(skill_dir: Path) -> list[Path]:
    """List skill files, excluding caches.

    Args:
        skill_dir: Skill root.

    Returns:
        list[Path]: Sorted files.
    """
    result = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_dir)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        result.append(path)
    return result


def read_version(skill_dir: Path) -> str:
    """Read metadata.version from SKILL.md.

    Args:
        skill_dir: Skill root.

    Returns:
        str: Version string.

    Raises:
        ValueError: When the frontmatter or version is missing.
    """
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if frontmatter is None:
        raise ValueError("SKILL.md has no frontmatter")
    match = re.search(r"(?m)^\s+version:\s*[\"']?([^\"'\s]+)", frontmatter.group(1))
    if match is None:
        raise ValueError("SKILL.md has no metadata.version")
    return match.group(1)


def read_manifest(path: Path) -> dict[str, str]:
    """Read a SHA-256 manifest.

    Args:
        path: Manifest path.

    Returns:
        dict[str, str]: Relative path to digest.

    Raises:
        ValueError: When a line is malformed.
    """
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError(f"malformed manifest line: {line!r}")
        values[parts[1]] = parts[0]
    return values


def compare(skill_dir: Path, expected: dict[str, str]) -> list[str]:
    """Compare a directory with a manifest.

    Args:
        skill_dir: Skill root.
        expected: Relative path to digest.

    Returns:
        list[str]: Differences.
    """
    actual = {path.relative_to(skill_dir).as_posix(): sha256(path) for path in files(skill_dir)}
    errors = []
    for relative, digest in sorted(expected.items()):
        if relative not in actual:
            errors.append(f"missing: {relative}")
        elif actual[relative] != digest:
            errors.append(f"modified: {relative}")
    for relative in sorted(set(actual) - set(expected)):
        errors.append(f"untracked: {relative}")
    return errors


def main() -> int:
    """Run the offline check.

    Returns:
        int: 0 when everything matches, 1 otherwise.
    """
    errors: list[str] = []
    source_path = MODULE_DIR / "SOURCE.toml"
    if not source_path.is_file():
        print(f"deep-research: {source_path} is missing", file=sys.stderr)
        return 1
    source = tomllib.loads(source_path.read_text(encoding="utf-8"))
    if source.get("skill") != SKILL_NAME:
        errors.append(f"SOURCE.toml skill is {source.get('skill')!r}")
    if not SKILL_DIR.is_dir():
        print(f"deep-research: {SKILL_DIR} is missing", file=sys.stderr)
        return 1
    try:
        version = read_version(SKILL_DIR)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        version = ""
    if version and source.get("version") != version:
        errors.append(f"SOURCE.toml version {source.get('version')!r} != SKILL.md {version!r}")
    manifest = MODULE_DIR / "SHA256SUMS"
    if not manifest.is_file():
        errors.append("SHA256SUMS is missing")
    else:
        try:
            errors.extend(compare(SKILL_DIR, read_manifest(manifest)))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    script = SKILL_DIR / "scripts" / "research.py"
    if not script.is_file():
        errors.append("scripts/research.py is missing")
    else:
        for flag in ("--version", "--help"):
            result = subprocess.run(
                [sys.executable, str(script), flag],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                errors.append(f"research.py {flag} exited {result.returncode}")
            elif flag == "--version" and version and version not in result.stdout:
                errors.append(f"research.py --version does not mention {version}")

    state_path = ROOT / "modules" / ".enabled.json"
    enabled = False
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            enabled = SKILL_NAME in state.get("modules", {})
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot read {state_path}: {exc}")
    if enabled and not INSTALLED_DIR.is_dir():
        errors.append("enabled copy is missing; run bin/modules.py enable deep-research --force")
    elif INSTALLED_DIR.is_dir() and manifest.is_file():
        try:
            installed_errors = compare(INSTALLED_DIR, read_manifest(manifest))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
        else:
            errors.extend(f"installed {item}" for item in installed_errors)

    if errors:
        for error in errors:
            print(f"deep-research: {error}", file=sys.stderr)
        return 1
    print(f"{SKILL_NAME}: ok (version {version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
