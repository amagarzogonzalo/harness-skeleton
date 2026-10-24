from __future__ import annotations

import json

import apply_profile
import pytest

CFG = {
    "roles": {
        "plan": "reasoning",
        "build": "coding",
        "review": "reasoning",
        "scribe": "cheap",
        "small": "cheap",
    },
    "routing": {},
}

PROFILE = {
    "name": "test",
    "models": {
        "reasoning": "reason/model",
        "coding": "code/model",
        "cheap": "cheap/model",
    },
}


def test_core_and_module_agents_get_models():
    generated = apply_profile.build(PROFILE, CFG, {"demo-reviewer": "review"})
    agents = generated["agent"]
    assert agents["critic"]["model"] == "openrouter/reason/model"
    assert agents["security-reviewer"]["model"] == "openrouter/reason/model"
    assert agents["build"]["model"] == "openrouter/code/model"
    assert agents["demo-reviewer"]["model"] == "openrouter/reason/model"
    assert generated[apply_profile.MANAGED]["module_agents"] == ["demo-reviewer"]


def test_unknown_module_role_fails():
    with pytest.raises(SystemExit):
        apply_profile.build(PROFILE, CFG, {"demo-reviewer": "does-not-exist"})


def test_merge_removes_stale_module_model_but_keeps_hand_written_keys():
    base = {
        "agent": {
            "demo-reviewer": {"model": "old", "permission": {"edit": "deny"}},
            "ghost": {"model": "old"},
        },
        apply_profile.MANAGED: {"module_agents": ["demo-reviewer", "ghost"]},
    }
    generated = apply_profile.build(PROFILE, CFG, {})

    merged = apply_profile.merge(base, generated)

    assert "model" not in merged["agent"]["demo-reviewer"]
    assert merged["agent"]["demo-reviewer"]["permission"] == {"edit": "deny"}
    assert "ghost" not in merged["agent"]


def test_enabled_module_agents_reads_the_state_file(tmp_path):
    state = tmp_path / "modules" / ".enabled.json"
    state.parent.mkdir(parents=True)
    state.write_text(
        json.dumps(
            {
                "modules": {
                    "lang-rust": {
                        "name": "lang-rust",
                        "role": "review",
                        "agents": ["rust-reviewer"],
                    }
                }
            }
        )
    )
    assert apply_profile.enabled_module_agents(tmp_path) == {"rust-reviewer": "review"}


def test_merge_preserves_hand_written_agent_permissions():
    base = {"agent": {"critic": {"permission": {"edit": "deny"}}}}
    generated = apply_profile.build(PROFILE, CFG, {})
    merged = apply_profile.merge(base, generated)
    assert merged["agent"]["critic"]["permission"] == {"edit": "deny"}
    assert merged["agent"]["critic"]["model"] == "openrouter/reason/model"


def test_merge_preserves_hand_written_commands():
    base = {"command": {"loop": {"template": "keep me"}}}
    generated = apply_profile.build(PROFILE, CFG, {})
    merged = apply_profile.merge(base, generated)
    assert merged["command"]["loop"]["template"] == "keep me"
