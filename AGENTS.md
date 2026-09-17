# AGENTS.md

A portable briefing for the coding agent. This is the template default — edit it
for your project: the real layout, your real commands, your hard rules. Keep it a
map, not an encyclopedia. `make context` enforces the token budget.

## Layout
| Path | What lives here |
|---|---|
| `src/` | Application code. Start at the module's entry point. |
| `tests/` | Unit tests. Fast, no network. |
| `evals/` | Behavioral regression suite (optional). |
| `harness.toml` | Model profiles, routing, context budgets. Change models here, not in agent files. |

## Commands (verbatim — do not improvise flags)
```
make install     make test      make lint      make types
make context     # what the always-on prompt costs
make check       # lint + types + context + test   <- the gate
```

## Hard rules
1. **Never commit** `.env`, keys, or credentials. **Never `git push`.** Stage and stop.
2. **Do not "fix" intentional ignores.** `# type: ignore[...]` / `# noqa:` with a
   trailing reason are deliberate. Leave them.
3. **No new dependency and no new MCP server without asking.** Every MCP tool schema
   is prompt weight on every turn, including turns that never call it.
4. **If a read or fetch fails, say so and stop.** Never substitute recalled knowledge
   for a lookup that failed.
5. **Do not raise a budget to make a check pass** — not the context budget, not a test
   threshold. Fix the thing, or say why the budget was wrong.

## Definition of done
`make check` is green, and you have stated in one line each:
- what behavior changed,
- what you did **not** do that a reviewer might expect.

## Conventions
- Set these for your stack: language, formatter, line length, type-check command.
- Commits: `area: imperative summary`.
- Errors: typed exceptions. Never bare `except:`.