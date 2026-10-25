# Setup

A verified path from a fresh machine to a working harness. The one-command
path is:

```bash
uv run python bin/bootstrap.py
```

`make setup` runs the same thing when `make` is installed. The bootstrap checks
the tools, installs the Python dependencies, and runs the offline context,
test, and module checks. It does not change models or write `.env`; those are
explicit choices below.

## 1. Prerequisites

- Python **3.11+**
- [`uv`](https://docs.astral.sh/uv/)
- `git`
- [OpenCode](https://opencode.ai/docs/)

On Windows, the OpenCode docs recommend **WSL** for the best compatibility.
Native Windows also works with Chocolatey, Scoop, or npm.

### Install OpenCode

```bash
npm install -g opencode-ai
```

Windows alternatives:

```powershell
choco install opencode
scoop install opencode
```

Verify:

```bash
opencode --version
```

The install commands above are from the official
[OpenCode install docs](https://opencode.ai/docs/#install). OpenCode 1 and 2
cannot be installed side by side under the default command; the harness targets
the `opencode` command in this repository.

## 2. Configure a provider

Run OpenCode and use its provider picker:

```bash
opencode
/connect
```

Or export the OpenRouter key before starting:

```bash
export OPENROUTER_API_KEY=...
```

The harness profiles use OpenRouter model IDs. If you use another provider,
change `profiles/*.toml` and `opencode.json` deliberately; see
[Models](https://opencode.ai/docs/models/).

## 3. Install the harness

From this checkout:

```bash
uv sync --no-install-project --all-extras
```

or:

```bash
make install
```

The bootstrap does this for you. It does **not** run `apply_profile` because
that writes model keys into `opencode.json`; that is a separate, deliberate
step.

## 4. Select a model profile

```bash
uv run python bin/apply_profile.py balanced
```

or, with `make`:

```bash
make profile P=balanced
```

`bin/apply_profile.py` fetches the OpenRouter catalog and validates every model
ID before writing `opencode.json`. If you are offline:

```bash
uv run python bin/apply_profile.py balanced --offline
```

### Why my model changed to Sonnet

The harness is profile-driven:

```text
harness.toml [roles]  -> capability (reasoning/coding/cheap)
profiles/*.toml       -> capability -> model ID
bin/apply_profile.py  -> model/provider keys in opencode.json
```

The active profile is `balanced`; it maps `reasoning` and `coding` to
`anthropic/claude-sonnet-4.5`. `bin/modules.py enable/disable` used to re-apply
that profile every time, which overwrote the model in `opencode.json`. It now
re-applies the profile **only for modules that bring agents**. Skill-only
modules such as `deep-research` leave your current model untouched.

Do not hand-edit `model`/`provider` in `opencode.json` and expect it to stick:
the next profile application owns those keys. Change `harness.toml` or
`profiles/*.toml`, then run `make profile P=<name>` (or the `uv run` command).

Project `opencode.json` overrides global OpenCode config, which is why the
repository's profile wins over a global model choice. See
[Config precedence](https://opencode.ai/docs/config/#precedence-order).

## 5. Verify the install

```bash
uv run python bin/context_budget.py
uv run pytest tests/ -q
uv run python bin/check_modules.py
```

If `make` is available, the full gate is:

```bash
make check
```

## 6. Modes: safe, auto, full

The default is `safe`. Setup does **not** change your model, agents, or
permissions. Choose a mode explicitly at launch:

| Mode | Prompts | Deny rules | Agent |
|---|---|---|---|
| `safe` | yes | enforced | project default (`plan`) |
| `auto` | no | enforced | `build` |
| `full` | no | **replaced by allow** | `build` |

```bash
uv run python bin/opencode_mode.py safe
uv run python bin/opencode_mode.py auto
uv run python bin/opencode_mode.py full
```

or, with `make`:

```bash
make safe
make auto
make full
```

The launcher sets `OPENCODE_PERMISSION` for that process only. It never edits
`opencode.json`, agent files, or models. A running session cannot change its
own mode; use the TUI command palette or relaunch with the command. `auto` is
the recommended unattended mode: it approves otherwise-asking requests but
keeps explicit denies, so `.env`, secret paths, `rm *`, and force-push remain
blocked. `full` replaces the
top-level permission block with `{"*": "allow"}` and selects `build`; agent
specific permissions in `opencode.json` still take precedence. It is a
deliberate escalation, so use it only in a container, on a topic branch, and
with push credentials removed.

Permissions are a policy boundary, not an isolation boundary; a script can
still call `os.remove`. See
[Permissions](https://opencode.ai/docs/permissions/) and the harness
[security rules](../.opencode/rules/security.md).

## 7. Agents

The harness ships five agents:

- `plan` and `build` are **primary**; switch with Tab.
- `critic`, `scribe`, and `security-reviewer` are **subagents**; invoke them
  with `@critic`, `@scribe`, or `@security-reviewer`, or let `build` task them.

Agent files live in `.opencode/agent/`. The inline definitions are in
`opencode.json` under `agent`. `default_agent` is `plan` (read-only); switch to
`build` when you want edits.

Verify what OpenCode loaded, from the repository root:

```bash
opencode agent list
opencode debug agent plan
```

If only `build` and `plan` appear, that is expected: the other three are
subagents and are not in the Tab switcher. If none of the harness agents appear,
run OpenCode from the repository root and confirm that both `opencode.json` and
`.opencode/agent/` were copied. See
[Agents](https://opencode.ai/docs/agents/) and
[`opencode agent list`](https://opencode.ai/docs/cli/#agent).

## 8. Skills

OpenCode discovers:

```text
.opencode/skills/<name>/SKILL.md
.agents/skills/<name>/SKILL.md
.claude/skills/<name>/SKILL.md
```

and their global equivalents. This repository's `deep-research` module is
enabled; see [the module README](../modules/deep-research/README.md).

### deep-research `.env`

Put the research-service configuration at the **repository root** where you use
the skill:

```dotenv
RESEARCH_BASE_URL=https://research-orchestration-agents.onrender.com
RESEARCH_TOKEN=<the service write token>
```

Never commit `.env`. The agent never reads it; the skill's script does. The
token is the service's `API_TOKEN`, not an LLM provider key.

Run:

```bash
uv run python .opencode/skills/deep-research/scripts/research.py health --json
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `opencode: command not found` | Install it with the commands above, or use WSL and install there. |
| `make: command not found` | Use the `uv run python ...` commands in this guide; `make` is a convenience. |
| Agents missing | Restart OpenCode; run from the repository root; check `opencode agent list` and that `opencode.json` plus `.opencode/agent/` exist. |
| Model changed after enabling a module | It was a module with agents; the active profile owns model keys. Change the profile, not `opencode.json`. |
| `OPENROUTER_API_KEY` missing | Run `opencode` → `/connect`, or export the key. |
| Profile validation fails | Re-pin the model IDs in `profiles/*.toml`; the catalog changed. |
| `uv sync` fails | Check network/proxy access to PyPI, then re-run. |

## Sources

- [OpenCode intro and install](https://opencode.ai/docs/#install)
- [OpenCode config and precedence](https://opencode.ai/docs/config/)
- [OpenCode permissions and auto mode](https://opencode.ai/docs/permissions/)
- [OpenCode Agent Skills](https://opencode.ai/docs/skills/)
- [OpenCode models](https://opencode.ai/docs/models/)
