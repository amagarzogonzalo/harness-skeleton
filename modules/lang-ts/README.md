# lang-ts

TypeScript/Node review, React guidance, strict typing, and an offline
lint/typecheck/test gate.

## Enable

```bash
make enable M=lang-ts
```

Adds `typescript-reviewer`, `react-reviewer`, `node-security-reviewer`,
`typescript-testing`, and `react-review`. All agents are read-only and mapped
to the `review` role.

The console and typecheck hooks are opt-in:

```bash
uv run python bin/modules.py enable lang-ts --with-hooks
```

`typecheck-on-edit` runs `tsc` after every TypeScript edit, debounced. On a large
repository it is slow; the gate already type-checks, so enable it only if you
want the earlier feedback.

## What the check runs

- Detects the package manager from the lockfile (`pnpm`, `yarn`, `bun`, `npm`).
- Runs `lint`, `typecheck`, and `test` scripts when they exist.
- Falls back to `tsc --noEmit` when there is a `tsconfig.json` but no
  `typecheck` script.
- Does not install dependencies; run the package manager's install first.

## What it does not do

- `npm audit`/`pnpm audit`: network. Run `audit.sh` or the scheduled CI job.
- Bundle analysis, Lighthouse, visual regression: separate tools.
- Auto-fixes: the gate reports; it does not rewrite the tree.

## Files

| File | Purpose |
|---|---|
| `agent/typescript-reviewer.md` | Types, async, modules, runtime validation |
| `agent/react-reviewer.md` | Hooks, effects, state, a11y, server/client |
| `agent/node-security-reviewer.md` | Injection, SSRF, auth, sessions, secrets |
| `skills/typescript-testing/SKILL.md` | Runner, async, type tests, mocks |
| `skills/react-review/SKILL.md` | Hooks, state, rendering, a11y |
| `hooks/no-console.js` | Warning toast for console.log (opt-in) |
| `hooks/typecheck-on-edit.js` | Debounced tsc after edits (opt-in, slow) |
| `check.sh` | Lint, typecheck, test |
| `audit.sh` | npm/pnpm/yarn/bun audit (network) |
| `tsconfig.strict.json` | Strict compiler starting point |
| `eslint.config.example.js` | Flat config with typescript-eslint and a11y |
| `package-scripts.fragment.json` | Scripts the gate looks for |
| `CI.fragment.yml` | CI job, pin the actions to SHAs |
