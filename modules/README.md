# Modules

Core is the repository root and is always active. A module is an opt-in folder
of agents, skills, hooks, and a check script. **An inactive module costs zero
context**: its files live outside the globs the harness reads.

## Commands

```bash
make modules                  # catalog, enabled state, detected stack markers
make enable M=lang-python     # copy the module's agents and skills into place
make disable M=lang-python    # remove only the files this module created
make check                    # gate; also runs every enabled module's check.sh
```

Hooks are not copied by `make enable`, because every file in
`.opencode/plugins/` loads at startup and runs with the harness's privileges.
Enable them deliberately:

```bash
uv run python bin/modules.py enable lang-rust --with-hooks
```

## What enable changes

| Source | Destination |
|---|---|
| `modules/<m>/agent/<name>.md` | `.opencode/agent/<name>.md` |
| `modules/<m>/skills/<skill>/**` | `.opencode/skills/<skill>/**` |
| `modules/<m>/hooks/*.js` (only with `--with-hooks`) | `.opencode/plugins/*.js` |
| `modules/<m>/check.sh` | run in place by `bin/check_modules.py` |
| `opencode.json` | `permission.task[<agent>] = "allow"` for each enabled agent |

`modules/.enabled.json` records every copied file, its SHA-256, and the previous
`permission.task` value for each agent. `disable` removes a file only when its
content still matches that hash, so work you edited is never deleted. Commit
`.enabled.json`; it is project state, not a cache.

## What enable does not change

- No model IDs are written into agent files. `bin/apply_profile.py` reads
  `.enabled.json` and maps each module agent to the role declared in
  `module.toml` (`review` by default). Run `make profile` only if you want to
  regenerate manually; `enable` does it for you.
- No `mcp` entries, no `tools`, and no permission changes other than the
  `permission.task` allowlist for the agents you enabled. `disable` restores the
  previous value (or removes the key). If a module needs another permission, it
  is a review item, not an automatic change.

## Module layout

```
modules/<name>/
  module.toml
  README.md
  agent/<name>.md
  skills/<name>/SKILL.md
  hooks/<name>.js          # optional, not loaded unless enabled
  check.sh                 # optional, offline, no network
  CI.fragment.yml          # optional, copy into .github/workflows/
  *.example                # optional config samples
```

`module.toml`:

```toml
name = "lang-python"
description = "Python review and test guidance."
status = "stable"                  # stable | preview
stack = ["pyproject.toml"]         # files that suggest this module
role = "review"                    # harness.toml [roles] key for its agents
agents = ["python-reviewer"]
skills = ["python-testing", "python-packaging"]
hooks = ["no-bare-except"]
check = "check.sh"
```

## Authoring rules

1. **Agents are read-only.** Set `edit: deny`, `task: deny`, and a narrow bash
   allowlist in the agent frontmatter. A reviewer that can edit is an advocate.
2. **No model IDs.** Use a role; `apply_profile.py` binds it to a capability.
3. **Descriptions are budget.** The agent description is charged on every
   request; keep it under 300 characters and lead with the trigger.
4. **One skill, one procedure.** The skill description is the only always-on
   part; make it match the words a user would actually use.
5. **Checks are offline.** No network in `check.sh`. Put `pip-audit`,
   `cargo audit`, `npm audit`, and mutation testing in an `audit.sh` or CI job.
6. **Hooks fail closed and explain themselves.** Throw an `Error` with the exact
   fix. Never auto-approve a permission.
7. **No secrets in examples.** Use `.env.example` with fake values.

## Removing a module

```bash
make disable M=<name>
```

Then delete `modules/<name>/` if you do not want it in the catalog. Run
`make context` and `make check`. If a copied agent was edited, `disable` leaves
it and prints `kept ...: modified since enable`; resolve it by hand.
