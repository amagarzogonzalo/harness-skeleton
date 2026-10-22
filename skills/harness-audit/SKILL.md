---
name: harness-audit
description: Audit the agent harness itself for context bloat, weak instructions, excessive tools, unsafe permissions, and missing verification. Trigger when the agent ignores instructions, context is near budget, or agents/skills/MCP servers were added.
---

# Harness audit

A harness is a prompt, a tool surface, a permission policy, and a gate. Audit all
four. Do not raise a budget to make a finding disappear.

## Six dimensions

Score each `ok`, `warn`, or `fail`, with one evidence line.

### 1. Context budget

```bash
make context
```

- Always-on total versus the 6000 budget.
- AGENTS.md over 100 lines: move procedures to skills.
- Skill descriptions over 400 chars: shorten; the body is free.
- Agent descriptions over 300 chars: shorten; every subagent description is paid
  on every turn.
- MCP servers: each one is schema weight even when unused. More than two needs a
  justification.
- Plugin custom tools: their schemas are not counted; remove or extend the meter.

### 2. Instruction quality

Read AGENTS.md and `.opencode/rules/`. For each rule, ask: is it testable, and
does a check enforce it? A rule with no check is a suggestion.
- Commands must be verbatim and runnable.
- Hard rules must say what to do when they conflict.
- No model-specific instructions (no "you are Claude/GPT").
- No duplicated rules across AGENTS.md and skills.

### 3. Tool surface

- Count tools, MCP servers, and subagents. Every one is a choice the model can
  make badly.
- Remove tools that no skill or command uses.
- Prefer a CLI the agent already knows over a custom tool schema.
- Verify agents have the permissions they need, and no more.

### 4. Model routing

```bash
make profiles
make sessions
```

- Every role maps to a capability, and every capability exists in the profile.
- Review runs on a different model than build, or explain why not.
- Cheap models are cheap per token, not per completed task. Check the sessions
  table for loops and retries.
- `require_parameters: true` and `transforms: []` are still set.

### 5. Permissions and secrets

Read `opencode.json` and `.opencode/rules/security.md`.
- `git push`, `rm`, `sudo`, `env`, and secret paths are denied.
- `git commit` is ask; `--no-verify` is denied.
- `task` allows only read-only subagents; `general` is denied.
- Secret-bearing paths are denied for `read`, `edit`, `glob`, and `grep`, not
  just `bash`.
- `env-protection` and `permission-audit` plugins are active.
- No auto-approve hook.

### 6. Verification

```bash
make check
make evals
```

- The gate runs every check the README claims.
- `artifacts/gate.json` is current; the commit guard rejects a stale marker.
- Evals cover the behaviors that matter, not just the demo.
- A failing test is fixed, not skipped.
- Coverage, mutation, and audits are nightly/CI, not pre-commit.

## Output

```
DIMENSION        SCORE  EVIDENCE
context          ok     total 2841 / 6000
instructions     warn   AGENTS.md rule 4 has no check
tools            ok     9 tools, 0 MCP
routing          ok     review != build
permissions      warn   grep can still reach .env through bash
verification     ok     make check green, 12 evals
```

Then list the **top three cuts**, each one line: what to remove or change, and
the token or risk saved. Do not list more than three; a 20-item audit is a list
nobody acts on.

## Rules

- Read before judging. A rule may already be enforced by a check.
- Do not propose adding a tool, MCP server, or agent as the first fix.
- Do not raise the context budget, coverage threshold, or timeout to pass.
- If a check failed, say which command and quote the first error line.
