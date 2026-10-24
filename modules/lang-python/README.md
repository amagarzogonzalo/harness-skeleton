# lang-python

Python review, pytest guidance, packaging, and an offline bandit check.

## Enable

```bash
make enable M=lang-python
```

This adds `python-reviewer`, `python-testing`, and `python-packaging`. The
agent is read-only and mapped to the `review` role. Disable with
`make disable M=lang-python`.

The bare-`except:` hook is not loaded by default:

```bash
uv run python bin/modules.py enable lang-python --with-hooks
```

## What the check runs

`check.sh` runs `bandit -q -ll -r src` when bandit is installed. It skips with a
message when it is not, because the harness does not add dependencies for you.
To activate it:

```bash
uv add --dev bandit
```

Core already runs `ruff`, `mypy`, and `pytest`; this module does not duplicate
them.

## What it does not do

- `pip-audit`, `safety`, and dependency resolution: network. Run `audit.sh` or
  the scheduled CI job, not the pre-commit gate.
- Coverage thresholds: configure them in `pyproject.toml` if the project wants
  them. Do not add an assertion-free test to raise a number.
- Auto-fixes: `check.sh` reports, it does not rewrite the tree.

## Files

| File | Purpose |
|---|---|
| `agent/python-reviewer.md` | Review checklist for a Python diff |
| `.opencode/skills/python-testing/SKILL.md` | pytest patterns and stop conditions |
| `.opencode/skills/python-packaging/SKILL.md` | pyproject, lockfile, build, versioning |
| `hooks/no-bare-except.js` | Blocks `except:` in Python edits (opt-in) |
| `check.sh` | Offline bandit |
| `audit.sh` | Network audit (not in the gate) |
| `ruff.toml.example` | Starting lint config |
| `pyproject.fragment.toml` | Dev deps and tool config |
| `CI.fragment.yml` | CI job, pin the actions to SHAs |
