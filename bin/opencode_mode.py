#!/usr/bin/env python3
"""Launch OpenCode in an explicit permission mode without editing config.

Modes:
    safe   Project permissions, prompts enabled, project default agent.
    auto   Build agent, ``--auto``; explicit deny rules still apply.
    full   Build agent, ``--auto``, permission allow; all deny rules replaced.

The mode is applied through ``OPENCODE_PERMISSION`` for the current process only.
`opencode.json`, `opencode.jsonc`, agent files, and models are never modified.

    uv run python bin/opencode_mode.py safe
    uv run python bin/opencode_mode.py auto
    uv run python bin/opencode_mode.py full
    uv run python bin/opencode_mode.py --print full
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

OPENCODE_INSTALL = (
    "opencode is not on PATH. Install it from https://opencode.ai/docs/#install:\n"
    "  npm install -g opencode-ai\n"
    "  choco install opencode   (Windows)\n"
    "  scoop install opencode   (Windows)\n"
    "  Windows: WSL is recommended"
)


@dataclass(frozen=True)
class Mode:
    """One launch mode.

    Attributes:
        name: Mode name.
        auto: Pass ``--auto`` to OpenCode.
        permission: Inline ``OPENCODE_PERMISSION`` value, when overridden.
        agent: Agent to select, when the mode should not use the project default.
        warning: Human warning printed before launch.
    """

    name: str
    auto: bool
    permission: str | None
    agent: str | None
    warning: str


MODES: dict[str, Mode] = {
    "safe": Mode(
        name="safe",
        auto=False,
        permission=None,
        agent=None,
        warning="",
    ),
    "auto": Mode(
        name="auto",
        auto=True,
        permission=None,
        agent="build",
        warning="auto mode: no prompts; explicit deny rules in opencode.json still apply.",
    ),
    "full": Mode(
        name="full",
        auto=True,
        permission=json.dumps({"*": "allow"}),
        agent="build",
        warning=(
            "FULL ACCESS: permission allow replaces every deny rule. "
            "Use only in a container, on a topic branch, with push credentials removed."
        ),
    ),
}


def build_command(mode: Mode, extra: list[str]) -> list[str]:
    """Build the OpenCode argument list for a mode.

    Args:
        mode: Selected mode.
        extra: Extra arguments passed after ``--``.

    Returns:
        list[str]: Command and arguments.
    """
    command = ["opencode"]
    if mode.auto:
        command.append("--auto")
    if mode.agent:
        command.extend(["--agent", mode.agent])
    command.extend(extra)
    return command


def build_env(mode: Mode) -> dict[str, str]:
    """Build the process environment for a mode.

    Args:
        mode: Selected mode.

    Returns:
        dict[str, str]: Environment with the permission override applied or cleared.
    """
    env = dict(os.environ)
    env.pop("OPENCODE_PERMISSION", None)
    if mode.permission is not None:
        env["OPENCODE_PERMISSION"] = mode.permission
    return env


def describe(mode: Mode, command: list[str]) -> str:
    """Render a human-readable mode summary.

    Args:
        mode: Selected mode.
        command: Command that would run.

    Returns:
        str: Summary text.
    """
    lines = [f"mode: {mode.name}"]
    if mode.permission is not None:
        lines.append(f"OPENCODE_PERMISSION={mode.permission}")
    lines.append("command: " + " ".join(command))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Launch OpenCode or print the selected mode.

    Args:
        argv: Arguments to parse; defaults to ``sys.argv``.

    Returns:
        int: OpenCode or error exit code.
    """
    parser = argparse.ArgumentParser(
        description="Launch OpenCode in an explicit permission mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", choices=sorted(MODES), help="safe, auto, or full")
    parser.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="print the mode, environment, and command without launching",
    )
    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="extra arguments after -- are passed to opencode",
    )
    args = parser.parse_args(argv)
    mode = MODES[args.mode]
    extra = [item for item in args.extra if item != "--"]
    command = build_command(mode, extra)
    if mode.warning:
        print(f"warning: {mode.warning}", file=sys.stderr)
    if args.print_only:
        print(describe(mode, command))
        return 0
    executable = shutil.which("opencode")
    if executable is None:
        print(OPENCODE_INSTALL, file=sys.stderr)
        return 1
    command[0] = executable
    return subprocess.run(command, env=build_env(mode), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
