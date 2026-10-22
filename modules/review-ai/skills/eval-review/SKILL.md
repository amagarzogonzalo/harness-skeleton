---
name: eval-review
description: Design or review an eval case for an LLM behavior. Trigger when adding a prompt, tool, agent, or model and you need a regression check.
---

# Eval review

## A case is a contract

Every case needs:

```
ID:         <stable, descriptive>
BEHAVIOR:   <the one thing it protects>
INPUT:      <prompt, files, tool fixtures>
EXPECTED:   <exact output, rubric, or assertion>
WHY:        <the bug this catches>
COST:       <offline replay | live call>
```

A case without `WHY` is a demo. A case without a fail condition is documentation.

## Design

1. **Pick the behavior, not the wording.** "Refuses a destructive tool call
   without confirmation" is a behavior. "Says exactly X" is brittle.
2. **Use a fake boundary.** Pin the model response with a cassette; pin tools,
   clock, and randomness. Offline replay must not call the network.
3. **One variable per case.** If the case changes the prompt and the model, a
   failure has two causes.
4. **Include the negative.** A case where the model should refuse, ask, or stop
   is as important as a happy path.
5. **Adversarial set.** Injection, empty input, contradictory instructions,
   tool failure, long context, non-English.
6. **Calibrate the judge.** If an LLM judges, give it a rubric with examples,
   pin its model, and check it against a human-scored sample. Watch verbosity
   and position bias.
7. **Threshold, not vibes.** A numeric threshold has a baseline and a margin.
   Do not lower it to pass; fix the behavior.

## Reviewing a change

- Would the new case fail on the old behavior? If not, it does not protect the
  change.
- Did an existing case change? That is a behavior change; a human must confirm.
- Is the snapshot update intentional? `--accept` without reading the diff is a
  regression disguised as a pass.
- Is the suite fast and cheap enough for CI? Live calls belong in a scheduled
  job with a budget.

## Stop conditions

- The case cannot fail: rewrite it or delete it.
- The case depends on a live model for a deterministic assertion: record it.
- The eval is more expensive than the bug it prevents: narrow it.
