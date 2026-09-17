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

Then: fill in `AGENTS.md` (`make agents` fails until the placeholders are gone),
and **check the model IDs in `profiles/*.toml`** — they're starting points, and
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
rules/context.md       634      27%
AGENTS.md              533      23%   45 lines
skill index             79       3%   2 skills
TOTAL                 2309   of 6000 budget
```

Skill *bodies* aren't counted — that's the point of progressive disclosure. Only
the index (name + description) is always-on, so a 400-line skill is free until it
triggers. The budget is enforced in CI, because context bloat is otherwise
invisible in review: nobody reads the prompt, AGENTS.md grows a section per
incident, and a year later every trivial request drags 20k tokens of preamble.

The cost isn't only money. Past a certain length models stop honoring the middle
of a long instruction block, so a bloated briefing file is *less obeyed* than a
short one.

Four levers, cheapest first (details in `.opencode/rules/context.md`): progressive
disclosure → retrieval over stuffing → cache-prefix discipline (static first,
volatile last) → tool-output compression. The last is optional and off by
default: `make compress-savings` measures it on your traffic before you commit to
another moving part. `bin/compress.sh` disables telemetry and user-scope installs
when you do enable it.

## Security

Permissions in `opencode.json` are a **policy** boundary — they stop the agent
from typing `rm -rf`, not from writing a Python script that calls `os.remove`.
That's why `python *`, `node *`, `uv run *` and `make *` are `ask` rather than
`allow`: arbitrary code execution routes around every other rule in the file.
Specific safe subcommands (`uv run pytest*`, `make test`) are allowed explicitly.

`.devcontainer/` is the isolation boundary. Run anything unattended or `--auto`
in there, on a branch, with `git push` denied. Note the API key is still readable
by processes inside the container — use a scoped, low-limit key for agent work.

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
.opencode/agent/          plan (read-only) · critic (adversarial) · scribe
skills/*/SKILL.md         procedures, loaded on demand
bin/apply_profile.py      profile -> opencode.json, with catalog validation
bin/context_budget.py     the always-on prompt tax, enforced
bin/sessions.py           cost per model, with turns/session
bin/compress.sh           optional tool-output compression proxy
evals/                    optional behavioral regression suite
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
