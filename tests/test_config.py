from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def config():
    return json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))


def test_gate_bypass_commands_stay_denied():
    permission = config()["permission"]
    # Push is a human-gated action, not a silent allow and not a hard deny.
    assert permission["bash"]["git push*"] == "ask"
    assert permission["bash"]["git commit*"] == "ask"
    assert permission["bash"]["git commit -n*"] == "deny"
    assert permission["bash"]["git commit*--no-verify*"] == "deny"
    assert permission["doom_loop"] == "ask"


def test_secret_paths_are_denied_for_file_tools_not_only_bash():
    permission = config()["permission"]
    for tool in ("read", "edit"):
        rules = permission[tool]
        assert rules["**/.env"] == "deny"
        assert rules["**/.env.example"] == "allow"
        assert rules["**/*.pem"] == "deny"
        assert rules["**/.ssh/**"] == "deny"
    for tool in ("glob", "grep"):
        assert permission[tool]["**/.env*"] == "deny"


def test_task_permission_is_an_allowlist():
    task = config()["permission"]["task"]
    assert task["*"] == "deny"
    assert task["critic"] == "allow"
    assert task["security-reviewer"] == "allow"
    assert task.get("general", "deny") == "deny"


def test_scribe_can_only_edit_documentation():
    scribe = config()["agent"]["scribe"]["permission"]["edit"]
    assert scribe["*"] == "deny"
    assert scribe["**/*.md"] == "allow"
    assert "**/*.py" not in scribe
    assert "**/*.ts" not in scribe


def test_reviewers_are_read_only_in_json():
    agents = config()["agent"]
    for name in ("critic",):
        assert agents[name]["permission"]["edit"] == "deny"


def test_loop_command_wires_the_bounded_loop_skill():
    command = config()["command"]["loop"]
    template = command["template"]
    assert command["description"]
    assert ".opencode/skills/loop/SKILL.md" in template
    assert "$ARGUMENTS" in template
    assert "artifacts/loop.md" in template
    assert "Do not commit or push" in template
