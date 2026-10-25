#!/usr/bin/env python3
"""Bootstrap a harness checkout without relying on `make`.

Checks the local prerequisites, installs the Python tooling with `uv`, runs the
offline context/test/module checks, and prints the remaining OpenCode steps. It
deliberately does not change `opencode.json` models or write `.env`; profile
selection and provider credentials are explicit human choices.

    uv run python bin/bootstrap.py
    uv run python bin/bootstrap.py --check
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 11)


def preflight() -> tuple[list[str], list[str]]:
    """Check local prerequisites and separate blockers from warnings.

    Returns:
        tuple[list[str], list[str]]: Blocking problems and advisory warnings.
    """
    blockers: list[str] = []
    warnings: list[str] = []
    if sys.version_info < MIN_PYTHON:
        blockers.append(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required; found {sys.version.split()[0]}"
        )
    for tool in ("uv", "git"):
        if shutil.which(tool) is None:
            blockers.append(f"{tool} is not on PATH")
    if shutil.which("opencode") is None:
        warnings.append(
            "opencode is not on PATH. Install it from https://opencode.ai/docs/#install:\n"
            "  npm install -g opencode-ai\n"
            "  choco install opencode   (Windows)\n"
            "  scoop install opencode   (Windows)\n"
            "  Windows: WSL is recommended for the best compatibility"
        )
    if not os.environ.get("OPENROUTER_API_KEY"):
        warnings.append(
            "OPENROUTER_API_KEY is not set. Run `opencode` and `/connect`, or export the key."
        )
    return blockers, warnings


def run(command: list[str]) -> int:
    """Run one command from the repository root.

    Args:
        command: Command and arguments.

    Returns:
        int: Command exit code.

    Raises:
        SystemExit: When the command fails.
    """
    print("$ " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


def next_steps() -> None:
    """Print the human steps that cannot be automated safely."""
    print(
        "\nNext:\n"
        "  1. opencode                 # then /connect if the provider is not configured\n"
        "  2. uv run python bin/apply_profile.py balanced\n"
        "     # or, if make is installed: make profile P=balanced\n"
        "  3. uv run python bin/context_budget.py\n"
        "  4. uv run python bin/opencode_mode.py safe|auto|full\n"
        "     # safe = prompts; auto = no prompts, denies kept; full = allow everything\n"
        "  5. opencode agent list    # verify plan/build/critic/scribe/security-reviewer\n"
        "  6. deep-research (optional): copy modules/deep-research/env.example to .env\n"
        "     and fill RESEARCH_BASE_URL / RESEARCH_TOKEN, then restart opencode.\n"
    )


def main(argv: list[str] | None = None) -> int:
    """Run the bootstrap.

    Args:
        argv: Arguments to parse; defaults to ``sys.argv``.

    Returns:
        int: Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the prerequisite checks only; do not install or test",
    )
    args = parser.parse_args(argv)

    blockers, warnings = preflight()
    for blocker in blockers:
        print(f"FAIL: {blocker}", file=sys.stderr)
    for warning in warnings:
        print(f"warn: {warning}", file=sys.stderr)
    if blockers:
        print("\nFix the blockers above, then re-run this script.", file=sys.stderr)
        return 1
    if args.check:
        print("prerequisites: ok (warnings are optional setup steps)")
        next_steps()
        return 0

    run(["uv", "sync", "--no-install-project", "--all-extras"])
    run(["uv", "run", "ruff", "check", "."])
    run(["uv", "run", "ruff", "format", "--check", "."])
    run(["uv", "run", "python", "bin/lint_agents.py"])
    run(["uv", "run", "python", "bin/context_budget.py"])
    run(["uv", "run", "pytest", "tests/", "-q"])
    run(["uv", "run", "python", "evals/runner.py"])
    run(["uv", "run", "python", "bin/check_modules.py"])
    print("\nbootstrap: ok")
    next_steps()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
