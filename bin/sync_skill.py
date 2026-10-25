#!/usr/bin/env python3
"""Vendor a skill from its canonical repository into a module.

The harness module system copies static files. This tool is the sanctioned way
to refresh a vendored skill: it copies the source tree, writes a `SOURCE.toml`
version record, and regenerates `SHA256SUMS`. The offline module check verifies
those hashes; this script is the only piece that needs the sibling repository.

    uv run python bin/sync_skill.py --module deep-research \
        --source ../projects/research-orchestration-agents/skills/deep-research

Use `--check` to compare the current vendored copy with the source without
writing anything. Use `--force` only when you intentionally want to discard
local edits in the vendored copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODULE = "deep-research"
DEFAULT_SOURCE = "../projects/research-orchestration-agents/skills/deep-research"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".env", ".env.*", ".git", "node_modules")


class SyncError(Exception):
    """A sync precondition or verification failed."""


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


def skill_files(skill_dir: Path) -> list[Path]:
    """List the files that make up a skill.

    Args:
        skill_dir: Skill root.

    Returns:
        list[Path]: Sorted regular files, excluding caches and secrets.
    """
    files: list[Path] = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_dir)
        if any(part == "__pycache__" for part in relative.parts):
            continue
        if path.suffix == ".pyc":
            continue
        if path.name == ".env" or path.name.startswith(".env."):
            continue
        files.append(path)
    return files


def read_skill_version(skill_dir: Path) -> str:
    """Read `metadata.version` from the skill frontmatter without PyYAML.

    Args:
        skill_dir: Skill root.

    Returns:
        str: Version string.

    Raises:
        SyncError: When SKILL.md or the version field is missing.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise SyncError(f"{skill_md} is missing")
    text = skill_md.read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if frontmatter is None:
        raise SyncError(f"{skill_md} has no frontmatter")
    version = re.search(r"(?m)^\s+version:\s*[\"']?([^\"'\s]+)", frontmatter.group(1))
    if version is None:
        raise SyncError(f"{skill_md} has no metadata.version")
    return version.group(1)


def write_checksums(skill_dir: Path, destination: Path) -> None:
    """Write a deterministic SHA-256 manifest for a skill directory.

    Args:
        skill_dir: Skill root.
        destination: Manifest path.
    """
    lines = []
    for path in skill_files(skill_dir):
        relative = path.relative_to(skill_dir).as_posix()
        lines.append(f"{sha256(path)}  {relative}")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_checksums(path: Path) -> dict[str, str]:
    """Read a SHA-256 manifest.

    Args:
        path: Manifest path.

    Returns:
        dict[str, str]: Relative path to digest.

    Raises:
        SyncError: When a line is malformed.
    """
    if not path.is_file():
        raise SyncError(f"{path} is missing")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise SyncError(f"{path} has a malformed line: {line!r}")
        values[parts[1]] = parts[0]
    return values


def verify_checksums(skill_dir: Path, manifest: Path) -> list[str]:
    """Verify a skill directory against a manifest.

    Args:
        skill_dir: Skill root.
        manifest: SHA-256 manifest.

    Returns:
        list[str]: Human-readable differences.
    """
    expected = read_checksums(manifest)
    actual = {
        path.relative_to(skill_dir).as_posix(): sha256(path) for path in skill_files(skill_dir)
    }
    errors: list[str] = []
    for relative, digest in sorted(expected.items()):
        if relative not in actual:
            errors.append(f"missing: {relative}")
        elif actual[relative] != digest:
            errors.append(f"modified: {relative}")
    for relative in sorted(set(actual) - set(expected)):
        errors.append(f"untracked: {relative}")
    return errors


def module_skill_name(module_dir: Path) -> str:
    """Read the skill name declared by a module manifest.

    Args:
        module_dir: Module directory.

    Returns:
        str: Declared skill name.

    Raises:
        SyncError: When the manifest is missing or declares no single skill.
    """
    manifest = module_dir / "module.toml"
    if not manifest.is_file():
        raise SyncError(f"{manifest} is missing")
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    skills = data.get("skills", [])
    if len(skills) != 1 or not isinstance(skills[0], str):
        raise SyncError(f"{manifest} must declare exactly one skill")
    return skills[0]


def source_toml(skill_dir: Path, *, repo: str, path: str, version: str) -> str:
    """Render the source manifest.

    Args:
        skill_dir: Skill root.
        repo: Canonical repository URL.
        path: Canonical path in that repository.
        version: Skill version.

    Returns:
        str: TOML document.
    """
    synced_at = datetime.now(UTC).isoformat()
    values = {
        "repo": repo,
        "path": path,
        "skill": skill_dir.name,
        "version": version,
        "synced_at": synced_at,
    }
    return "".join(f"{key} = {json.dumps(value)}\n" for key, value in values.items())


def sync(root: Path, module: str, source: Path, *, force: bool, check_only: bool) -> int:
    """Sync or check one vendored skill.

    Args:
        root: Harness repository root.
        module: Module name.
        source: Canonical skill directory.
        force: Discard local edits in the vendored copy.
        check_only: Compare without writing.

    Returns:
        int: Process exit code.

    Raises:
        SyncError: When a precondition or verification fails.
    """
    module_dir = root / "modules" / module
    if not module_dir.is_dir():
        raise SyncError(f"unknown module {module!r}: {module_dir} is missing")
    declared = module_skill_name(module_dir)
    if source.name != declared:
        raise SyncError(f"source skill is {source.name!r}, module expects {declared!r}")
    if not (source / "SKILL.md").is_file() or not (source / "scripts" / "research.py").is_file():
        raise SyncError(f"{source} is not a complete deep-research skill")

    destination = module_dir / "skills" / declared
    manifest = module_dir / "SHA256SUMS"
    source_version = read_skill_version(source)

    if check_only:
        errors: list[str] = []
        if destination.is_dir():
            try:
                module_version = read_skill_version(destination)
            except SyncError as exc:
                errors.append(str(exc))
            else:
                if module_version != source_version:
                    errors.append(
                        f"version mismatch: module {module_version}, source {source_version}"
                    )
            errors.extend(verify_checksums(destination, manifest))
        else:
            errors.append("not vendored")
        if errors:
            for error in errors:
                print(f"deep-research: {error}", file=sys.stderr)
            return 1
        print(f"deep-research: {source_version} is in sync")
        return 0

    if destination.exists():
        if not manifest.is_file():
            raise SyncError(f"{manifest} is missing; cannot prove the vendored copy is clean")
        differences = verify_checksums(destination, manifest)
        if differences and not force:
            raise SyncError(
                "vendored copy has local changes; inspect with --check or pass --force: "
                + ", ".join(differences[:3])
            )
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=IGNORE)
    write_checksums(destination, manifest)
    (module_dir / "SOURCE.toml").write_text(
        source_toml(
            destination,
            repo="https://github.com/amagarzogonzalo/research-orchestration-agents",
            path="skills/deep-research",
            version=source_version,
        ),
        encoding="utf-8",
    )
    print(f"synced {module} skill {source_version} -> {destination}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the sync parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Vendor a skill from its canonical repository into a harness module."
    )
    parser.add_argument("--module", default=DEFAULT_MODULE, help="module name")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="canonical skill directory")
    parser.add_argument("--check", action="store_true", help="compare without writing")
    parser.add_argument(
        "--force", action="store_true", help="discard local edits in the vendored copy"
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the sync tool.

    Args:
        argv: Arguments to parse; defaults to ``sys.argv``.

    Returns:
        int: Process exit code.
    """
    args = build_parser().parse_args(argv)
    source = Path(args.source).expanduser()
    if not source.is_absolute():
        source = ROOT / source
    try:
        code = sync(ROOT, args.module, source.resolve(), force=args.force, check_only=args.check)
    except (SyncError, OSError, tomllib.TOMLDecodeError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"ok": code == 0, "module": args.module, "source": str(source)}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
