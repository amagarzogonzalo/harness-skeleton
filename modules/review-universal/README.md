# review-universal

Language-agnostic reviewers for the checks every change needs but no linter
covers.

## Agents

| Agent | Finds |
|---|---|
| `test-reviewer` | Missing cases, weak assertions, flaky tests, tests that cannot fail |
| `dependency-reviewer` | Lockfile risk, CVEs, licenses, provenance, install scripts |
| `api-reviewer` | Contract breaks, idempotency, pagination, errors, limits |
| `performance-reviewer` | Complexity, N+1, allocations, caching, missing benchmarks |
| `docs-reviewer` | Wrong commands, stale examples, missing changelog, dead links |
| `release-reviewer` | Versioning, migration, rollback, flags, artifacts |

## Skills

- `test-review` — map changed behavior to a test that can fail.
- `api-review` — classify the contract change and trace authz/retries/limits.
- `release-review` — release checklist with a named rollback.

## Enable

```bash
make enable M=review-universal
```

Six agents are added to the task index. If that is too much context, keep the
module disabled and copy only the agent files you need into `.opencode/agent/`,
then add those names to `permission.task`. `make enable` is all-or-nothing by
design; partial enablement is a manual edit.

## Notes

- All agents are read-only and mapped to the `review` role.
- No check script: these are review procedures, not automated gates.
- `dependency-reviewer` does not run a network audit. It reviews the lockfile
  diff and tells you what to verify; CI owns the scanner.
- The reviewers do not edit. If a finding needs a fix, the build agent applies
  it and the reviewer re-reads the diff.
