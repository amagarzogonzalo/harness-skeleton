# Optional hooks

These are examples, not defaults. Nothing in this directory is loaded until you
copy a file into `.opencode/plugins/` and restart opencode.

```bash
cp hooks/optional/secret-scan.js .opencode/plugins/
```

Every file in `.opencode/plugins/` loads at startup and runs with the harness's
privileges. Read the source before enabling it. A plugin can read the
environment, spawn processes, and write files; it is not a sandbox.

## Catalog

| Hook | Event | Behavior | Risk if enabled |
|---|---|---|---|
| `secret-scan.js` | `tool.execute.before` (write/edit/bash) | Blocks high-confidence key patterns | False positive on a test fixture; narrow the pattern |
| `dangerous-command.js` | `tool.execute.before` (bash) | Blocks destructive commands | False positive on a string in a script; review the rules |
| `format-on-edit.js` | `event: file.edited` | Runs ruff/rustfmt/prettier | Formatter rewrites the file after the agent read it; race |
| `lint-on-edit.js` | `event: file.edited` | Runs ruff/eslint/clippy, toast on error | Slow on Rust; duplicates the gate |
| `notification.js` | `event: session.idle/session.error` | TUI toast | Noisy; most clients already notify |
| `shell-env.js` | `shell.env` | Adds `HARNESS=1`, unbuffered Python | Environment mismatch; never put secrets here |
| `checkpoint-on-idle.js` | `event: session.idle` | Writes `artifacts/last-idle.json` | A heartbeat, not a checkpoint; low value |

## Core plugins (already active)

`.opencode/plugins/` contains four single-purpose hooks:

| Plugin | Why it is core |
|---|---|
| `env-protection.js` | Closes the `read`/`write`/`edit` and `rg` gap on secret paths |
| `commit-guard.js` | Refuses `git commit` without current gate evidence |
| `compaction-context.js` | Preserves task, files, and gate state across compaction |
| `permission-audit.js` | Records every permission request and reply |

## Not recommended

| Hook | Why |
|---|---|
| Auto-approve (`permission.ask` sets `allow`) | Removes the last human gate; the exact anti-pattern |
| A monolithic hooks plugin copied from another harness | Missing scripts, stale context, TS-only imports, auto-approve |
| Test on every edit / mutation on idle | Slow, noisy, duplicate the gate; run in CI/nightly |
| Coverage on every edit | Same; coverage is not a correctness signal |
| Custom tools that wrap `git diff` or `ls` | Their schemas are always-on prompt weight; the CLI already exists |
| A second `plugins/index.ts` next to a hooks file | Double-loads every handler |

## Load order and cost

- Global config plugins load, then project config, then global plugin files,
  then project plugin files. A duplicate local/npm plugin loads twice.
- Plugin **code** is not prompt context. A plugin that registers a **tool** is:
  the schema is attached to every request. `bin/context_budget.py` warns when it
  sees a `tool:` block but cannot count the schema.
- Hooks that fire on every tool call (`tool.execute.before`) must be cheap. A
  regex is fine; a subprocess on every call is not.
