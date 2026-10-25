#!/usr/bin/env python3
"""Install the deep-research skill into a repository or a global agent path.

The installer copies the whole skill directory, including the client script and
this installer, into the client's skill directory. It never reads or writes
``.env``; configuration stays in the target repository.

Examples:
    python scripts/install.py --repo .
    python scripts/install.py --repo ../my-project --agents
    python scripts/install.py --global
    python scripts/install.py --repo . --uninstall
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SKILL_NAME = "deep-research"
SKILL_ROOT = Path(__file__).resolve().parents[1]
EXIT_USAGE = 2
EXIT_IO = 3
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".env", ".env.*", ".git", "node_modules")


class InstallError(Exception):
    """Installation failed with an actionable message."""


def resolve_target(args: argparse.Namespace) -> Path:
    """Resolve the final skill directory from CLI options.

    Args:
        args: Parsed arguments.

    Returns:
        Path: Absolute target skill directory.

    Raises:
        InstallError: When the options disagree or the target is unsafe.
    """
    if args.target:
        target = Path(args.target).expanduser().resolve()
        if target.name != SKILL_NAME:
            raise InstallError(f"--target must end with {SKILL_NAME!r}; got {target.name!r}")
        return target
    if args.global_install:
        if args.agents:
            return Path.home() / ".agents" / "skills" / SKILL_NAME
        return Path.home() / ".config" / "opencode" / "skills" / SKILL_NAME
    repo = Path(args.repo).expanduser().resolve()
    if args.agents:
        return repo / ".agents" / "skills" / SKILL_NAME
    return repo / ".opencode" / "skills" / SKILL_NAME


def validate_source() -> None:
    """Check that this directory is a complete skill.

    Raises:
        InstallError: When a required file is missing.
    """
    required = (SKILL_ROOT / "SKILL.md", SKILL_ROOT / "scripts" / "research.py")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise InstallError(f"skill source is incomplete; missing: {', '.join(missing)}")


def validate_target(target: Path) -> None:
    """Reject targets that would delete or overwrite the source tree.

    Args:
        target: Resolved target directory.

    Raises:
        InstallError: When the target and source overlap.
    """
    source = SKILL_ROOT.resolve()
    if target == source:
        raise InstallError("target is the source skill directory; choose another location")
    if target.is_relative_to(source):
        raise InstallError("target is inside the source skill directory")
    if source.is_relative_to(target):
        raise InstallError("target contains the source skill directory; choose another location")


def install(target: Path, *, force: bool, dry_run: bool, json_output: bool) -> int:
    """Copy the skill to the target.

    Args:
        target: Resolved target directory.
        force: Replace an existing target.
        dry_run: Print actions without changing files.
        json_output: Emit JSON.

    Returns:
        int: Process exit code.

    Raises:
        InstallError: When the target exists and force is not set.
    """
    validate_source()
    validate_target(target)
    if target.exists() and not target.is_dir():
        raise InstallError(f"{target} exists but is not a directory")
    if target.exists():
        if not force:
            raise InstallError(f"{target} already exists; use --force to replace it or --uninstall to remove it")
        action = "replace"
    else:
        action = "install"
    if dry_run:
        if json_output:
            print(json.dumps({"ok": True, "action": action, "target": str(target), "dry_run": True}))
        else:
            print(f"would {action} {target}")
        return 0
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL_ROOT, target, ignore=IGNORE)
    files = sum(1 for path in target.rglob("*") if path.is_file())
    if json_output:
        print(json.dumps({"ok": True, "action": action, "target": str(target), "files": files}))
    else:
        print(f"{action}ed {SKILL_NAME} -> {target} ({files} files)")
    return 0


def uninstall(target: Path, *, dry_run: bool, json_output: bool) -> int:
    """Remove an installed skill directory.

    Args:
        target: Resolved target directory.
        dry_run: Print actions without changing files.
        json_output: Emit JSON.

    Returns:
        int: Process exit code.

    Raises:
        InstallError: When the target is the source tree.
    """
    validate_target(target)
    if not target.exists():
        if json_output:
            print(json.dumps({"ok": True, "action": "absent", "target": str(target)}))
        else:
            print(f"{target} is not installed")
        return 0
    if not target.is_dir():
        raise InstallError(f"{target} exists but is not a directory")
    if dry_run:
        if json_output:
            print(json.dumps({"ok": True, "action": "remove", "target": str(target), "dry_run": True}))
        else:
            print(f"would remove {target}")
        return 0
    shutil.rmtree(target)
    if json_output:
        print(json.dumps({"ok": True, "action": "remove", "target": str(target)}))
    else:
        print(f"removed {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the installer parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(
        description=f"Install or remove the {SKILL_NAME} Agent Skill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  install.py --repo .\n"
            "  install.py --repo ../my-project --agents\n"
            "  install.py --global\n"
            "  install.py --repo . --uninstall\n"
        ),
    )
    parser.add_argument("--repo", default=".", help="repository to install into (default .)")
    parser.add_argument("--global", dest="global_install", action="store_true", help="install for the current user")
    parser.add_argument("--agents", action="store_true", help="use the cross-client .agents/skills path")
    parser.add_argument("--target", help="exact target directory; must end with deep-research")
    parser.add_argument("--force", action="store_true", help="replace an existing installation")
    parser.add_argument("--uninstall", action="store_true", help="remove the installed skill")
    parser.add_argument("--dry-run", action="store_true", help="print actions without changing files")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the installer.

    Args:
        argv: Arguments to parse; defaults to ``sys.argv``.

    Returns:
        int: Process exit code.
    """
    args = build_parser().parse_args(argv)
    try:
        target = resolve_target(args)
        if args.uninstall:
            return uninstall(target, dry_run=args.dry_run, json_output=args.json)
        return install(target, force=args.force, dry_run=args.dry_run, json_output=args.json)
    except InstallError as exc:
        payload = {"ok": False, "error": {"code": "install", "message": str(exc)}}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except OSError as exc:
        payload = {"ok": False, "error": {"code": "io", "message": f"I/O error: {exc}"}}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"error: I/O error: {exc}", file=sys.stderr)
        return EXIT_IO


if __name__ == "__main__":
    raise SystemExit(main())
