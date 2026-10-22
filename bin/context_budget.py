#!/usr/bin/env python3
"""Measure the context you pay for on EVERY request, and fail when it grows.

    python bin/context_budget.py            # report + enforce
    python bin/context_budget.py --report   # report only, never fails

Context bloat is invisible by construction: nobody sees the prompt, so AGENTS.md
grows a section per incident, three MCP servers get added for one task each, and
six months later every trivial request drags 20k tokens of preamble. The cost is
not only money — past a certain length models demonstrably stop honoring the
middle of a long instruction block, so a bloated briefing file is *less obeyed*
than a short one.

This makes that number visible and gates it like any other budget.

What counts as always-on:
  AGENTS.md, everything in .opencode/rules/, every file named in
  opencode.json:instructions, the skill INDEX (name + description of each skill,
  which the model must see to know the skill exists), the agent INDEX (the task
  tool lists subagents by name + description), and MCP tool schemas.
What does not: skill BODIES, agent prompt bodies, and command templates. That is
the point of progressive disclosure — a body costs nothing until it triggers.
Custom tool schemas registered by a plugin are also not counted; the report
warns when a plugin registers one, because a silent undercount is worse than a
visible warning.
"""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILTIN_AGENTS = {"plan", "build", "explore", "general"}


def count_tokens(text: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:  # noqa: BLE001 -- tiktoken is optional; char/3.7 fallback is intentional
        # ~3.7 chars/token for English prose+markdown. Within ~10% of a real
        # tokenizer, which is enough to catch a doubling.
        return round(len(text) / 3.7)


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip("\"'")
    return out


def agent_descriptions(root: Path, conf: dict) -> dict[str, str]:
    """Merge agent descriptions from markdown files and opencode.json.

    Markdown wins on a conflict: it is the file a reviewer edits when changing
    the agent, and `opencode.json` descriptions are usually a short duplicate.
    """
    from_md: dict[str, str] = {}
    agent_dir = root / ".opencode" / "agent"
    if agent_dir.exists():
        for path in sorted(agent_dir.glob("*.md")):
            fm = frontmatter(path.read_text(encoding="utf-8"))
            name = fm.get("name", path.stem)
            description = fm.get("description", "")
            if description:
                from_md[name] = description

    from_json: dict[str, str] = {}
    for name, entry in conf.get("agent", {}).items():
        if isinstance(entry, dict) and entry.get("description"):
            from_json[name] = entry["description"]

    merged: dict[str, str] = {}
    for name in sorted(set(from_md) | set(from_json)):
        description = from_md.get(name) or from_json.get(name, "")
        if description:
            merged[name] = description
    return merged


def collect(root: Path = ROOT) -> tuple[list[tuple[str, int, str]], list[str]]:
    rows: list[tuple[str, int, str]] = []
    warnings: list[str] = []
    cfg = tomllib.loads((root / "harness.toml").read_text(encoding="utf-8"))
    limits = cfg.get("context", {})

    agents_md = root / "AGENTS.md"
    if agents_md.exists():
        text = agents_md.read_text(encoding="utf-8")
        n = len(text.splitlines())
        rows.append(("AGENTS.md", count_tokens(text), f"{n} lines"))
        if n > limits.get("agents_md_max_lines", 100):
            warnings.append(
                f"AGENTS.md is {n} lines (limit {limits['agents_md_max_lines']}). "
                "Move a procedure into skills/ — skills cost nothing until triggered."
            )
    else:
        warnings.append("no AGENTS.md — every tool that reads it gets nothing")

    for rule in sorted((root / ".opencode" / "rules").glob("*.md")):
        rows.append((f"rules/{rule.name}", count_tokens(rule.read_text(encoding="utf-8")), ""))

    opencode = root / "opencode.json"
    conf = json.loads(opencode.read_text(encoding="utf-8")) if opencode.exists() else {}

    for extra in conf.get("instructions", []):
        if any(ch in extra for ch in "*?["):
            continue
        path = root / extra
        if path.exists() and path.name != "AGENTS.md":
            rows.append(
                (f"instructions/{path.name}", count_tokens(path.read_text(encoding="utf-8")), "")
            )

    skill_index, skills = [], sorted((root / "skills").glob("*/SKILL.md"))
    over_skills = []
    for skill in skills:
        fm = frontmatter(skill.read_text(encoding="utf-8"))
        name, desc = fm.get("name", skill.parent.name), fm.get("description", "")
        skill_index.append(f"{name}: {desc}")
        if len(desc) > limits.get("skill_description_max", 400):
            over_skills.append(f"{name} ({len(desc)} chars)")
        if not desc:
            warnings.append(f"skill {name!r} has no description — it will never trigger")
    if skill_index:
        rows.append(("skill index", count_tokens("\n".join(skill_index)), f"{len(skills)} skills"))
    if over_skills:
        warnings.append(f"skill descriptions over budget: {', '.join(over_skills)}")

    agent_map = agent_descriptions(root, conf)
    if agent_map:
        agent_index = [f"{name}: {desc}" for name, desc in agent_map.items()]
        rows.append(
            ("agent index", count_tokens("\n".join(agent_index)), f"{len(agent_map)} agents")
        )
        over_agents = [
            f"{name} ({len(desc)} chars)"
            for name, desc in agent_map.items()
            if len(desc) > limits.get("agent_description_max", 300)
        ]
        if over_agents:
            warnings.append(f"agent descriptions over budget: {', '.join(over_agents)}")

    task = conf.get("permission", {}).get("task", {})
    if isinstance(task, dict):
        known = set(agent_map) | BUILTIN_AGENTS
        for name, action in task.items():
            if name != "*" and action != "deny" and name not in known:
                warnings.append(
                    f"permission.task allows {name!r}, but no such agent is defined in "
                    ".opencode/agent/ or opencode.json:agent"
                )

    plugin_dir = root / ".opencode" / "plugins"
    if plugin_dir.exists():
        for plugin in sorted(plugin_dir.iterdir()):
            if plugin.suffix not in {".js", ".ts", ".mjs", ".cjs"}:
                continue
            if re.search(r"\btool\s*:\s*\{", plugin.read_text(encoding="utf-8", errors="ignore")):
                warnings.append(
                    f"plugin {plugin.name} registers custom tools. Their schemas are attached "
                    "to every request but are NOT counted above — extend this meter or remove "
                    "the tool."
                )

    mcp = conf.get("mcp", {})
    if mcp:
        # Schemas live on the servers, so this is a floor, not the real number.
        # Run `opencode` and check the session token count for the true figure.
        est = 350 * len(mcp)
        rows.append(("MCP servers (est.)", est, f"{len(mcp)} servers"))
        warnings.append(
            f"{len(mcp)} MCP server(s) configured. Every tool schema is prompt weight on "
            "every turn, including turns that will never call it. The estimate above is a "
            "floor — check a real session's token count."
        )
    return rows, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="never exit non-zero")
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    cfg = tomllib.loads((root / "harness.toml").read_text(encoding="utf-8"))
    budget = cfg.get("context", {}).get("always_on_token_budget", 6000)
    rows, warnings = collect(root)
    total = sum(tokens for _, tokens, _ in rows)

    width = max((len(name) for name, _, _ in rows), default=10)
    print(f"{'source'.ljust(width)}  {'tokens':>7}   {'share':>6}")
    print("-" * (width + 22))
    for name, tokens, note in sorted(rows, key=lambda row: -row[1]):
        share = f"{tokens / total:.0%}" if total else "-"
        print(f"{name.ljust(width)}  {tokens:>7}   {share:>6}  {note}")
    print("-" * (width + 22))
    print(f"{'TOTAL'.ljust(width)}  {total:>7}   of {budget} budget")

    # A number nobody can feel is a number nobody acts on.
    print(
        f"\nThat is {total} tokens attached to every request. Across 200 requests a day "
        f"that is {total * 200 / 1_000_000:.1f}M input tokens/day before you ask anything."
    )

    for warning in warnings:
        print(f"\nwarn: {warning}")

    if total > budget:
        biggest = max(rows, key=lambda row: row[1])[0] if rows else "nothing"
        print(
            f"\nFAIL: {total} > {budget}. Biggest contributor is {biggest}. Cut it, or "
            "raise the budget in harness.toml with a comment saying why."
        )
        return 0 if args.report else 1
    print(f"\nOK: {budget - total} tokens of headroom.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
