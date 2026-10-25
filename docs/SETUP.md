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

## 6. Full access / auto mode

The safe default keeps prompts in place. If you explicitly want an unattended
session with no questions, OpenCode has a built-in auto mode:

```bash
opencode --auto
```

In the TUI, the command palette has **Enable auto-approve permissions**. Auto
mode approves requests that would otherwise ask; explicit `deny` rules are
still enforced. That means the harness's secret-path, `.env`, destructive-shell,
and force-push denies remain blocked. This is the official per-session mode, not
an auto-approve hook, and the harness does not enable it by default.

`make auto` is a shortcut for `opencode --auto`.

Use auto mode only inside a container, on a topic branch, and with push
credentials removed or denied. Permissions are a policy boundary, not an
isolation boundary; a script can still call `os.remove`. See
[Permissions](https://opencode.ai/docs/permissions/) and the harness
[security rules](../.opencode/rules/security.md).

If you want a permanent permissive policy, set `permission: "allow"` in
`opencode.json`, but that also removes the secret/destructive denies. The
harness does not do this by default.

## 7. Skills

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
