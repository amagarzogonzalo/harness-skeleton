# AGENTS.md — <PROJECT NAME>

<!-- MAP, NOT ENCYCLOPEDIA. 100-line hard budget, enforced by `make context`. -->
<!-- Adding a procedure? Write a skill in skills/. This file is taxed on every request. -->
<!-- Model-agnostic on purpose: this repo switches models. No "you are Claude", no -->
<!-- provider-specific prompt tricks, no assumptions about reasoning-trace behavior. -->

## What this is
<One sentence: what the system does and for whom.>
<One sentence: the non-obvious thing a new engineer gets wrong.>

## Layout
| Path | What lives here |
|---|---|
| `src/` | Core package. Start at `src/<entry>`. |
| `tests/` | Unit tests. Fast, no network. |
| `harness.toml` | Model profiles, routing, context budgets. Change models here, not in agent files. |

## Commands (verbatim — do not improvise flags)
```
make install     make test      make lint      make types
make context     # what the always-on prompt costs
make check       # lint + types + context + test   <- the gate
```

## Hard rules
1. **Never commit** `.env`, keys, or credentials. **Never `git push`.** Stage and stop.
2. **Do not "fix" intentional ignores.** `# type: ignore[...]` / `# noqa:` with a trailing
   reason comment are deliberate.
3. **No new dependency and no new MCP server without asking.** Every MCP tool schema is
   prompt weight on every turn, including turns that never call it.
4. **If a read or fetch fails, say so and stop.** Never substitute recalled knowledge for
   a lookup that failed.
5. **Do not raise a budget to make a check pass** — not the context budget, not a test
   threshold. Fix the thing, or say why the budget was wrong.

## Definition of done
`make check` is green, and you have stated in one line each:
- what behavior changed,
- what you did **not** do that a reviewer might expect.

## Conventions
- <language/toolchain, line length, formatter>
- Commits: `area: imperative summary`.
- Errors: typed exceptions from `src/errors`. Never bare `except:`.
