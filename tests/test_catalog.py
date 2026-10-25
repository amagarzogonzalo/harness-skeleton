from __future__ import annotations

import tomllib
from pathlib import Path

import context_budget

ROOT = Path(__file__).resolve().parents[1]


def manifests():
    for path in sorted((ROOT / "modules").glob("*/module.toml")):
        yield path.parent, tomllib.loads(path.read_text(encoding="utf-8"))


def module_agents():
    for base, manifest in manifests():
        for name in manifest.get("agents", []):
            yield base / "agent" / f"{name}.md"


def module_skills():
    for base, manifest in manifests():
        for name in manifest.get("skills", []):
            yield base / "skills" / name / "SKILL.md"


def all_agents():
    yield from sorted((ROOT / ".opencode" / "agent").glob("*.md"))
    yield from module_agents()


def all_skills():
    seen: set[str] = set()
    for path in sorted((ROOT / ".opencode" / "skills").glob("*/SKILL.md")):
        seen.add(path.parent.name)
        yield path
    for path in module_skills():
        if path.parent.name not in seen:
            yield path


def test_core_skills_live_where_opencode_discovers_them():
    found = {path.parent.name for path in (ROOT / ".opencode" / "skills").glob("*/SKILL.md")}
    expected = {"checkpoint", "harness-audit", "loop", "new-skill", "ship", "tdd"}
    assert expected <= found, f"missing from .opencode/skills: {sorted(expected - found)}"


def test_core_skills_are_exposed_in_the_tui():
    for name in ("checkpoint", "harness-audit", "new-skill", "ship", "tdd"):
        text = (ROOT / ".opencode" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert 'opencode/slash: "true"' in text, f"{name}: not exposed as a /command"


def test_every_declared_module_file_exists():
    for base, manifest in manifests():
        assert manifest.get("name") == base.name, f"{base}: name mismatch"
        for name in manifest.get("agents", []):
            assert (base / "agent" / f"{name}.md").is_file(), f"{base.name}: {name}"
        for name in manifest.get("skills", []):
            assert (base / "skills" / name / "SKILL.md").is_file(), f"{base.name}: {name}"
        for name in manifest.get("hooks", []):
            hook = base / "hooks" / name
            assert hook.is_file(), f"{base.name}: {name}"
            assert hook.suffix == ".js", f"{base.name}: {name} must be plain JS"


def test_agents_have_a_short_description_and_no_model():
    limit = tomllib.loads((ROOT / "harness.toml").read_text(encoding="utf-8"))
    max_chars = limit.get("context", {}).get("agent_description_max", 300)

    for path in all_agents():
        text = path.read_text(encoding="utf-8")
        fm = context_budget.frontmatter(text)
        assert fm.get("description"), f"{path}: missing description"
        assert len(fm["description"]) <= max_chars, f"{path}: description over {max_chars} chars"
        assert "model" not in fm, f"{path}: model IDs belong in harness.toml, not the agent"
        assert fm.get("mode") in {"subagent", "primary", "all"}, f"{path}: mode is required"


def test_reviewers_are_read_only():
    reviewer_dirs = [ROOT / ".opencode" / "agent"]
    reviewer_dirs += [base / "agent" for base, _ in manifests()]
    for directory in reviewer_dirs:
        for path in sorted(directory.glob("*.md")):
            if path.stem in {"plan", "critic", "scribe"}:
                continue
            text = path.read_text(encoding="utf-8")
            assert "edit: deny" in text, f"{path}: reviewer can edit"
            assert "task: deny" in text, f"{path}: reviewer can spawn subagents"


def test_skill_names_are_unique_and_match_the_directory():
    seen: dict[str, Path] = {}
    for path in all_skills():
        fm = context_budget.frontmatter(path.read_text(encoding="utf-8"))
        name = fm.get("name", path.parent.name)
        assert name == path.parent.name, f"{path}: name {name!r} != directory"
        assert name not in seen, f"duplicate skill {name!r}: {seen[name]} and {path}"
        seen[name] = path
        assert fm.get("description"), f"{path}: missing description"


def test_skill_descriptions_fit_the_always_on_budget():
    max_chars = tomllib.loads((ROOT / "harness.toml").read_text(encoding="utf-8"))["context"].get(
        "skill_description_max", 400
    )
    for path in all_skills():
        description = context_budget.frontmatter(path.read_text(encoding="utf-8")).get(
            "description", ""
        )
        assert len(description) <= max_chars, f"{path}: description over {max_chars} chars"
