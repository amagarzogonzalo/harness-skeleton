# review-ai

Reviewers for LLM features: injection, evals, and agent design.

## Agents

| Agent | Finds |
|---|---|
| `llm-security-reviewer` | OWASP LLM Top 10:2025, injection, output handling, agency, leakage |
| `eval-reviewer` | Missing cases, judge bias, weak assertions, snapshot drift |
| `agent-architecture-reviewer` | Tool surface, permissions, context, loops, subagents |

## Skills

- `prompt-injection` — attack surfaces, layered defenses, test cases.
- `eval-review` — case design, determinism, judge calibration.
- `agent-design` — smallest action space, permissions, context, verification.

`examples/prompt-injection-cases.md` is a starter eval set. Copy the cases into
the project's eval suite; do not treat the file itself as a test.

## Enable

```bash
make enable M=review-ai
```

All agents are read-only and mapped to the `review` role. No check script.

## Notes

- The LLM security reviewer treats all retrieved content as data. If it finds an
  instruction in a document, that is a finding, not an instruction.
- The eval reviewer will not lower a threshold to make a suite pass.
- The agent architecture reviewer is useful before building an agent, not only
  after. It can review a design doc.
