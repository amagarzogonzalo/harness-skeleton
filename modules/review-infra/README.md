# review-infra

Infrastructure reviewers for CI, IaC, supply chain, and containers.

## Agents

| Agent | Finds |
|---|---|
| `ci-reviewer` | Triggers, permissions, pinning, secrets, injection, cache poisoning |
| `infra-reviewer` | IAM, exposure, encryption, state, blast radius, resilience |
| `supply-chain-reviewer` | SLSA, SBOM, provenance, signing, dependency confusion |
| `container-reviewer` | Base image, non-root, capabilities, secrets, limits |

## Skills

- `ci-security` — GitHub Actions checklist and safe pattern.
- `iac-review` — read the plan, classify create/replace/destroy.
- `supply-chain-review` — source/build/artifact/distribution/consumer.

## Enable

```bash
make enable M=review-infra
```

All agents are read-only and mapped to the `review` role. No check script.

## Notes

- These reviewers need the plan/manifest, not only the diff. If they do not have
  it, they will say which findings are provisional.
- The CI reviewer is specific to GitHub Actions. For GitLab CI or Jenkins, adapt
  the checks; do not pretend the action-pinning rules apply.
- The supply-chain reviewer checks claims. It does not sign or publish anything.
