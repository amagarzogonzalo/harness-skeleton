# review-risk

Risk reviewers for the questions that do not show up in a diff: who can attack
this, what data does it keep, can we operate it, and can we undo it.

## Agents

| Agent | Finds |
|---|---|
| `threat-modeler` | Assets, trust boundaries, STRIDE threats, residual risk |
| `privacy-reviewer` | PII, minimization, retention, deletion, third parties |
| `observability-reviewer` | Missing metrics/logs/traces/alerts/runbooks |
| `migration-reviewer` | Expand/contract, locks, backfills, rollback |
| `database-reviewer` | Indexes, plans, N+1, transactions, constraints |

## Skills

- `threat-model` — worksheet with STRIDE and residual risk.
- `migration-review` — expand/contract procedure.

`policies/severity.md` is the shared severity rubric. Copy it into the project's
review docs if the team has no equivalent.

## Enable

```bash
make enable M=review-risk
```

All agents are read-only and mapped to the `review` role. No check script.

## Notes

- The threat modeler is useful before implementation, not only after. It can
  review a design doc as well as a diff.
- The privacy reviewer flags engineering questions; it does not give legal
  advice. Route the questions to the privacy owner.
- The migration reviewer never runs a migration against production.
