# Severity policy

Shared by the reviewers in this repository. The label is about impact and
evidence, not about how strongly the reviewer feels.

| Label | Meaning | Action |
|---|---|---|
| `BLOCKER` | Data loss, security breach, or a release that cannot be rolled back | Do not merge/ship |
| `CRITICAL` | Exploitable security issue, or a failure that corrupts data | Fix before merge |
| `HIGH` | A user-visible bug, a missing test for a changed behavior, or a production outage path | Fix before merge, or state why not |
| `MEDIUM` | A real defect with limited blast radius, or a maintainability issue that will cause one | Fix in this change or file a tracked issue |
| `LOW` | A nitpick with no behavioral impact | Optional; do not pad the review |

## Evidence rules

- `confirmed`: traced to a reachable path, with `file:line`.
- `suspected`: plausible, but the reviewer could not read the code path. Say
  what would confirm it.
- A security finding needs an attacker, a path, and an impact. Otherwise it is
  `suspected`, not `CRITICAL`.
- A performance finding needs a number or a plan. "Slow" is not a finding.
- A test finding needs the behavior and the test that would fail. "Add tests" is
  not a finding.

## What is never a finding

- Formatting, naming, or import order owned by the linter.
- "Consider using X" without a behavioral reason.
- A rewrite of the module when a two-line fix closes the issue.
- A vulnerability in a test fixture presented as production risk.
