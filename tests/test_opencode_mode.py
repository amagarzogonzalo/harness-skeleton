from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "opencode_mode.py"


def run_mode(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--print", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_safe_mode_launches_without_auto():
    result = run_mode("safe")
    assert result.returncode == 0
    assert "mode: safe" in result.stdout
    assert "command: opencode" in result.stdout
    assert "--auto" not in result.stdout


def test_auto_mode_keeps_project_denies():
    result = run_mode("auto")
    assert result.returncode == 0
    assert "mode: auto" in result.stdout
    assert "--auto" in result.stdout
    assert "--agent build" in result.stdout
    assert "OPENCODE_PERMISSION" not in result.stdout
    assert "explicit deny" in result.stderr


def test_full_mode_sets_permission_allow():
    result = run_mode("full")
    assert result.returncode == 0
    assert "mode: full" in result.stdout
    assert 'OPENCODE_PERMISSION={"*": "allow"}' in result.stdout
    assert "--auto" in result.stdout
    assert "FULL ACCESS" in result.stderr


def test_extra_arguments_are_forwarded():
    result = run_mode("auto", "--", "--model", "openrouter/example/model")
    assert result.returncode == 0
    assert "--model openrouter/example/model" in result.stdout
