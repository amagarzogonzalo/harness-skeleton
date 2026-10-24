# harness/ — a provider-agnostic agent harness for opencode

Drop into any repo. Gives you four things that survive a changing model, a
changing codebase, and six months of drift:

1. **One-command model switching** across every agent, validated against the live
   OpenRouter catalog.
2. **A context budget that is measured and enforced**, so the prompt tax you pay
   on every request can't grow invisibly.
3. **Permissions scoped to risk**, with an actual isolation boundary behind them.
4. **Behavioral regression tests** for LLM-driven code (optional module).

## Install

```bash
cp -r harness/. your-repo/
cd your-repo
export OPENROUTER_API_KEY=...       # or: opencode /connect
make profile P=balanced             # validates model IDs, writes opencode.json
make context                        # what your always-on prompt costs
make evals                          # green out of the box via evals/_demo.py
```

Then: fill in `AGENTS.md` (it ships with generic defaults so `make agents` passes
out of the box — replace the layout/commands/rules with your project's), and
**check the model IDs in `profiles/*.toml`** — they're starting points, and
`make profile` will reject any that no longer exist and suggest replacements.

## Switching models

Agents never name a model. They ask for a **capability**; `harness.toml` maps
roles to capabilities; `profiles/*.toml` bind capabilities to OpenRouter IDs.

```bash
make profiles              # list
make profile P=frontier    # switches plan, build, critic, scribe, judge at once
```

`bin/apply_profile.py` owns the `model` / `provider` / per-agent model keys in
`opencode.json` and preserves everything hand-written. CI fails if the two drift
apart, so the config can't silently diverge from the profile.

Two routing settings are load-bearing and set for you:

- `require_parameters: true` — without it OpenRouter may route to a provider that
  silently ignores parameters you sent (tool choice, reasoning effort, response
  format). You will debug the *model* for a day before suspecting the route.
- `transforms: []` — set **explicitly**. Omitting the key is not the same:
  OpenRouter's middle-out transform activates on over-long prompts and deletes
  the middle of your context without telling you. Better to fail loudly.

Use opencode's **built-in** openrouter provider, as this config does, rather than
a custom `@ai-sdk/openai-compatible` one — model-level options are known to be
dropped on custom providers in headless mode.

## Context efficiency

`make context` prints what every request costs before you've asked anything:

```
source              tokens    share
AGENTS.md              592      25%   49 lines
rules/context.md       542      23%
rules/models.md        534      23%
rules/security.md      394      17%
skill index            224       9%   6 skills
agent index             81       3%   4 agents
TOTAL                 2367   of 6000 budget
```

Skill *bodies* and agent prompt bodies aren't counted — that's the point of
progressive disclosure. Only the index (name + description) is always-on, so a
400-line skill is free until it triggers. The budget is enforced in CI, because
context bloat is otherwise invisible in review: nobody reads the prompt,
AGENTS.md grows a section per incident, and a year later every trivial request
drags 20k tokens of preamble.

The cost isn't only money. Past a certain length models stop honoring the middle
of a long instruction block, so a bloated briefing file is *less obeyed* than a
short one.

Four levers, cheapest first (details in `.opencode/rules/context.md`): progressive
disclosure → retrieval over stuffing → cache-prefix discipline (static first,
volatile last) → tool-output compression. The last is optional and off by
default: `make compress-savings` measures it on your traffic before you commit to
another moving part. `bin/compress.sh` disables telemetry and user-scope installs
when you do enable it.

## Trying a loop

A loop is allowed when "done" is a command, not a feeling. The procedure lives in
`.opencode/skills/loop/SKILL.md`; the `/loop` command is a shortcut that points at it.
Run it from the **build** agent (the plan agent cannot edit).

```text
/loop GOAL: make the parser tests pass | CHECK: make test | CAP: 5
```

- `GOAL` — the observable end state.
- `CHECK` — the exact command that proves it. If this is missing, the loop stops
  and asks; it does not guess.
- `CAP` — maximum attempts. The skill defaults to 10; use 3–5 for a first run.

Every iteration is appended to `artifacts/loop.md` (gitignored), including the
hypothesis, files changed, result, and next action. The skill's stop matrix ends
the loop on success, two identical failures, no progress, a missing tool, or a
change that would touch a hard rule or budget. It ends with a `STATUS` block.

`/check` is the narrower loop: run `make check`, fix the smallest thing, re-run.
It has no iteration cap or written evidence, so use it for small gate failures.

Without the command, paste the header from `.opencode/skills/loop/SKILL.md` and tell the
agent to read that file first. Do not use `--auto` outside `.devcontainer/`, and
do not commit or push from inside a loop.

The other core skills are exposed as `/tdd`, `/checkpoint`, `/new-skill`,
`/harness-audit`, and `/ship`. Module skills appear after `make enable M=<module>`
and an opencode restart.

## Modules (opt-in)

Core is the repository root. Everything else is a module: a folder of agents,
skills, hooks, and a check script that costs **zero context** until enabled.

```bash
make modules                  # catalog + detected stack markers
make enable M=lang-python     # add the Python reviewers and skills
make disable M=lang-python    # remove only the files this module created
```

`modules/.enabled.json` records every copied file and its SHA-256, so `disable`
never deletes a file you edited. Module checks run only when the module is
enabled, not merely because a `pyproject.toml` or `Cargo.toml` exists.

| Module | What it adds |
|---|---|
| `review-universal` | test, dependency, API, performance, docs, release reviewers |
| `review-risk` | threat model, privacy, observability, migration, database reviewers |
| `review-ai` | LLM security, eval, and agent-architecture reviewers |
| `review-web` | accessibility, frontend, GraphQL, browser-security reviewers |
| `review-infra` | CI, IaC, supply-chain, container reviewers |
| `lang-python` | python reviewer, pytest/packaging skills, bandit check |
| `lang-rust` | rust and unsafe reviewers, testing skills, fmt/clippy/test |
| `lang-ts` | TypeScript/React/Node reviewers, testing skills, lint/tsc/test |

Four plugins are active in `.opencode/plugins/`: `env-protection` (secret paths
through `read`/`write`/`edit`/`rg`), `commit-guard` (refuses a commit without a
current gate marker), `compaction-context` (preserves task and gate state across
compaction), and `permission-audit` (local JSONL audit trail). They are plain
JavaScript: no build step, no new dependency. Example hooks live in
`hooks/optional/` and are **not** loaded until copied.

`make check` now also runs `bin/check_modules.py` and writes
`artifacts/gate.json`. The pre-commit hook (`.githooks/pre-commit`, installed
with `make install-hooks`) runs the same gate.

## Security

Permissions in `opencode.json` are a **policy** boundary — they stop the agent
from typing `rm -rf`, not from writing a Python script that calls `os.remove`.
That's why `python *`, `node *`, `uv run *` and `make *` are `ask` rather than
`allow`: arbitrary code execution routes around every other rule in the file.
Specific safe subcommands (`uv run pytest*`, `make test`) are allowed explicitly.
`git push` is `ask`: the agent can push only after you approve the prompt.
Unattended runs should remove push credentials rather than rely on the prompt.

Secret-bearing paths (`.env`, `*.pem`, `.ssh/`, `.aws/`, `*credentials*`) are
denied for `read`, `edit`, `glob`, and `grep`, not only for `bash`. `env-protection`
is a second layer for `rg KEY .env` and similar. It is still not a sandbox:
`python -c "open('.env').read()"` can read it if the permission engine allows the
interpreter. The devcontainer is the isolation boundary.

`.devcontainer/` is the isolation boundary. Run anything unattended or `--auto`
in there, on a branch, with push credentials removed (or `git push` denied in the
container). Note the API key is still readable by processes inside the container
— use a scoped, low-limit key for agent work.

## The eval module (optional)

Delete `evals/` if your project isn't LLM-driven. If it is, this catches the
failure unit tests can't see: a graph that still "works" but drifted.

Snapshot-diffing raw LLM prose doesn't work — output changes every run, the diff
is always red, you stop reading it. This diffs a **structural projection**
instead:

| Layer | Catches | Cost |
|---|---|---|
| Invariants (`lib/invariants.py`) | broken contracts, dropped citations, uncited claims, budget blowouts | free, deterministic |
| Digest snapshot (`lib/digest.py`) | silent structural drift — frontmatter shape, heading tree, citation set | free, deterministic |
| Judge (`lib/judge.py`) | reasoning quality, tone | slow, paid, fallible |

Reword a paragraph → silent. Drop a source → `BREAKING`.

Four things it does that most eval suites don't: `samples: 3` with `pass_at_k`
(a single green run isn't evidence, and differing *shapes* across samples is
reported as `NONDETERMINISM` before anything else is believed); cassette
record/replay so PR evals are free, offline and attributable to your change;
token and call budgets asserted like any other invariant; and a judge that must
reproduce known-good and known-bad calibration scores before its verdict counts.

The judge model is pinned in `harness.toml` and deliberately does **not** follow
your active profile — a judge that changes when you switch models silently
re-bases every historical score.

## Layout

```
harness.toml              roles, profiles, routing, context budgets   <- start here
profiles/*.toml           capability -> OpenRouter model id
AGENTS.md                 the map. Model-agnostic, 100-line budget.
opencode.json             permissions + agents (hand-written) / models (generated)
.opencode/rules/          models · context · security
.opencode/agent/          plan (read-only) · critic · scribe · security-reviewer
.opencode/plugins/        env-protection · commit-guard · compaction · audit
.opencode/skills/*/SKILL.md  procedures, loaded on demand
modules/                  opt-in agents/skills/hooks/checks; zero cost until enabled
hooks/optional/           example hooks, not loaded until copied
bin/apply_profile.py      profile -> opencode.json, with catalog validation
bin/context_budget.py     the always-on prompt tax, enforced
bin/modules.py            enable/disable/list the opt-in catalog
bin/gate_marker.py        write/verify artifacts/gate.json for the commit guard
bin/check_modules.py      run checks for enabled modules only
bin/sessions.py           cost per model, with turns/session
bin/compress.sh           optional tool-output compression proxy
tests/                    unit tests for the harness itself
evals/                    optional behavioral regression suite
.githooks/pre-commit      make check before a commit (make install-hooks)
.devcontainer/            the isolation boundary
```

## Verified, and not

Tested end to end here: profile apply + config merge (hand-written config
preserved), context budget, AGENTS lint, and the eval suite passing, failing on a
real regression, and recovering. Catalog validation degrades correctly when
offline.

Not verified: the specific model IDs in `profiles/*.toml` (no catalog access from
where this was built — `make profile` will tell you), and opencode's config schema
evolves, so if a field is rejected check https://opencode.ai/docs/config.
