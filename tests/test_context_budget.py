from __future__ import annotations

import json

import context_budget


def make_root(tmp_path, budget=6000):
    (tmp_path / "harness.toml").write_text(
        "\n".join(
            [
                "[context]",
                "agents_md_max_lines = 100",
                f"always_on_token_budget = {budget}",
                "skill_description_max = 400",
                "agent_description_max = 300",
            ]
        )
        + "\n"
    )
    (tmp_path / "AGENTS.md").write_text("# Test\n\nA short briefing.\n")
    (tmp_path / ".opencode" / "rules").mkdir(parents=True)
    (tmp_path / ".opencode" / "rules" / "security.md").write_text("# Security\n")
    (tmp_path / ".opencode" / "agent").mkdir(parents=True)
    (tmp_path / ".opencode" / "agent" / "foo.md").write_text(
        "---\ndescription: markdown description\nmode: subagent\n---\nbody\n"
    )
    skill = tmp_path / ".opencode" / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\ndescription: demo skill\n---\nbody\n")
    (tmp_path / "opencode.json").write_text(
        json.dumps(
            {
                "agent": {
                    "foo": {"description": "json description"},
                    "bar": {"description": "bar description"},
                },
                "permission": {"task": {"*": "deny", "foo": "allow"}},
                "mcp": {},
            }
        )
    )
    return tmp_path


def test_agent_descriptions_merge_and_markdown_wins(tmp_path):
    root = make_root(tmp_path)
    conf = json.loads((root / "opencode.json").read_text())
    descriptions = context_budget.agent_descriptions(root, conf)
    assert descriptions["foo"] == "markdown description"
    assert descriptions["bar"] == "bar description"


def test_collect_includes_agent_and_skill_indices(tmp_path):
    root = make_root(tmp_path)
    rows, _ = context_budget.collect(root)
    names = {name for name, _, _ in rows}
    assert "agent index" in names
    assert "skill index" in names


def test_unknown_task_agent_is_a_warning(tmp_path):
    root = make_root(tmp_path)
    conf = json.loads((root / "opencode.json").read_text())
    conf["permission"]["task"]["ghost"] = "allow"
    (root / "opencode.json").write_text(json.dumps(conf))

    _, warnings = context_budget.collect(root)
    assert any("ghost" in warning for warning in warnings)


def test_plugin_custom_tool_is_flagged(tmp_path):
    root = make_root(tmp_path)
    plugins = root / ".opencode" / "plugins"
    plugins.mkdir(parents=True)
    (plugins / "custom.js").write_text("export const P = async () => ({ tool: { hello: {} } });\n")

    _, warnings = context_budget.collect(root)
    assert any("custom tools" in warning for warning in warnings)


def test_over_budget_fails_unless_report(tmp_path, capsys):
    root = make_root(tmp_path, budget=1)
    assert context_budget.main(["--root", str(root)]) == 1
    assert context_budget.main(["--root", str(root), "--report"]) == 0
    assert "FAIL" in capsys.readouterr().out
