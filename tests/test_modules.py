from __future__ import annotations

import json

import modules


def make_module(root):
    base = root / "modules" / "demo"
    (base / "agent").mkdir(parents=True)
    (base / "skills" / "demo-skill").mkdir(parents=True)
    (base / "hooks").mkdir(parents=True)
    (base / "module.toml").write_text(
        """\
name = "demo"
description = "demo module"
status = "stable"
stack = ["marker.txt"]
role = "review"
agents = ["demo-reviewer"]
skills = ["demo-skill"]
hooks = ["demo-hook.js"]
check = "check.sh"
"""
    )
    (base / "agent" / "demo-reviewer.md").write_text("---\ndescription: demo\n---\nbody\n")
    (base / "skills" / "demo-skill" / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: demo skill\n---\nbody\n"
    )
    (base / "hooks" / "demo-hook.js").write_text("export const Demo = async () => ({});\n")
    (base / "check.sh").write_text("#!/usr/bin/env bash\nset -e\nexit 0\n")
    return base


def state(root):
    return json.loads((root / "modules" / ".enabled.json").read_text())


def test_enable_copies_agents_and_skills_not_hooks(tmp_path):
    make_module(tmp_path)
    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=False) == 0

    assert (tmp_path / ".opencode" / "agent" / "demo-reviewer.md").exists()
    assert (tmp_path / ".opencode" / "skills" / "demo-skill" / "SKILL.md").exists()
    assert not (tmp_path / ".opencode" / "plugins" / "demo-hook.js").exists()

    data = state(tmp_path)
    assert "demo" in data["modules"]
    assert len(data["modules"]["demo"]["files"]) == 2


def test_enable_with_hooks_copies_them(tmp_path):
    make_module(tmp_path)
    assert modules.enable(tmp_path, "demo", force=False, with_hooks=True, dry_run=False) == 0
    assert (tmp_path / ".opencode" / "plugins" / "demo-hook.js").exists()


def test_enable_is_idempotent(tmp_path):
    make_module(tmp_path)
    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=False) == 0
    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=False) == 0
    assert len(state(tmp_path)["modules"]["demo"]["files"]) == 2


def test_existing_unrecorded_file_blocks_enable(tmp_path):
    make_module(tmp_path)
    target = tmp_path / ".opencode" / "agent" / "demo-reviewer.md"
    target.parent.mkdir(parents=True)
    target.write_text("hand-written\n")

    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=False) == 1
    assert target.read_text() == "hand-written\n"
    assert not (tmp_path / "modules" / ".enabled.json").exists()


def test_force_overwrites_files_the_module_created(tmp_path):
    make_module(tmp_path)
    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=False) == 0

    target = tmp_path / ".opencode" / "agent" / "demo-reviewer.md"
    target.write_text("edited\n")

    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=False) == 1
    assert modules.enable(tmp_path, "demo", force=True, with_hooks=False, dry_run=False) == 0
    assert "body" in target.read_text()


def test_disable_removes_only_unmodified_recorded_files(tmp_path):
    make_module(tmp_path)
    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=False) == 0

    edited = tmp_path / ".opencode" / "agent" / "demo-reviewer.md"
    edited.write_text("my edit\n")
    user_file = tmp_path / ".opencode" / "skills" / "demo-skill" / "NOTES.md"
    user_file.write_text("mine\n")

    assert modules.disable(tmp_path, "demo", dry_run=False) == 0
    assert edited.exists()
    assert user_file.exists()
    assert not (tmp_path / ".opencode" / "skills" / "demo-skill" / "SKILL.md").exists()
    assert "demo" not in state(tmp_path)["modules"]


def test_dry_run_writes_nothing(tmp_path):
    make_module(tmp_path)
    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=True) == 0
    assert not (tmp_path / ".opencode" / "agent" / "demo-reviewer.md").exists()
    assert not (tmp_path / "modules" / ".enabled.json").exists()


def test_enable_grants_and_disable_revokes_task_permission(tmp_path):
    make_module(tmp_path)
    config = tmp_path / "opencode.json"
    config.write_text(json.dumps({"permission": {"task": {"*": "deny"}}}))

    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=False) == 0
    task = json.loads(config.read_text())["permission"]["task"]
    assert task["demo-reviewer"] == "allow"
    assert state(tmp_path)["modules"]["demo"]["task_permissions"] == {"demo-reviewer": None}

    assert modules.disable(tmp_path, "demo", dry_run=False) == 0
    task = json.loads(config.read_text())["permission"]["task"]
    assert "demo-reviewer" not in task
    assert task["*"] == "deny"


def test_existing_deny_is_respected_and_restored(tmp_path):
    make_module(tmp_path)
    config = tmp_path / "opencode.json"
    config.write_text(json.dumps({"permission": {"task": {"*": "deny", "demo-reviewer": "deny"}}}))

    assert modules.enable(tmp_path, "demo", force=False, with_hooks=False, dry_run=False) == 0
    task = json.loads(config.read_text())["permission"]["task"]
    assert task["demo-reviewer"] == "deny"
    assert state(tmp_path)["modules"]["demo"]["task_permissions"]["demo-reviewer"] == "deny"

    assert modules.disable(tmp_path, "demo", dry_run=False) == 0
    task = json.loads(config.read_text())["permission"]["task"]
    assert task["demo-reviewer"] == "deny"


def test_list_reports_the_catalog(tmp_path, capsys):
    make_module(tmp_path)
    assert modules.list_modules(tmp_path) == 0
    out = capsys.readouterr().out
    assert "demo" in out
    assert "enabled: none" in out
