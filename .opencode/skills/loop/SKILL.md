---
name: loop
description: Iterate toward a verifiable goal, adjusting scope as you learn. Use for multi-step edit-run-inspect work, even when the exact check is not known yet. Use `/loop GOAL: ... | CHECK: ... | CAP: 5`.
---

# Loop

A loop makes progress visible: try something, run a check, learn, repeat. The
check can start rough and get sharper as you understand the repo.

Use a loop when the work needs more than one edit-run-inspect cycle. For a
one-step change, make the change and verify it once.

## Start

Establish a baseline before changing anything:

1. Run the check you intend to use. Record pass/fail and the key line.
2. If it already passes, the goal is either done or the check is wrong. Stop
   and say which.
3. Write the loop header. Infer missing pieces; do not stall.

```
GOAL:     <observable end state>
CHECK:    <the proof you will run each iteration>
CAP:      <max iterations, default 5>
EVIDENCE: <where results are recorded — artifacts/loop.md>
```

- **GOAL** — use the user's. If unstated, infer it from the request and repo
  and state it in one line. If you learn it was wrong, rewrite it explicitly.
- **CHECK** — use the user's. If unstated, pick the strongest proof available:
  the project gate (`make check`), the nearest test, the build, a repro
  command, or a manual probe. Say which and why.
- If no check exists, create the smallest one that would show the goal is met.
  A manual probe counts.
- Ask only when "done" is genuinely ambiguous *and* a wrong guess would be
  expensive. A rough check you actually run beats a perfect one you don't.

### Choosing checks

- Use a fast, deterministic check each iteration; run the full gate once at the
  end.
- Prefer a check that fails for the right reason over one that merely errors.
- If a check is flaky, rerun it once. If it flakes again, treat it as a blocker,
  not as progress.
- Never relax the check to make it pass. If the check itself is wrong, fix it
  deliberately and say why.

## Each iteration

1. State the one hypothesis you are testing.
2. Make the smallest change that tests it. Touch unrelated code only when the
   hypothesis requires it; note unrelated failures instead of fixing them.
3. Run the check. Keep the command and the key output.
4. Decide: continue, change approach, or stop.

Batch changes only when they are independent and you can still tell which one
moved the result.

## When to stop

Stop when the check passes or when continuing is no longer worth it. Report the
reason in either case:

- The check passes — run the project gate once (`make check`), then report.
- The same failure repeats and the hypothesis is clearly wrong.
- Two iterations with no measurable progress — record what you ruled out.
- The check cannot run (missing tool, permission) — report the blocker.
- The next step needs a human decision (hard rule, budget, dependency).
- Context is running low — checkpoint, then stop or split the task.

These are judgment calls, not tripwires. If a different move is clearly better,
say so and make it.

## Guardrails

- Do not weaken, skip, or delete a test, threshold, coverage target, or context
  budget to pass.
- No `--no-verify`, no force-push, no rewriting history.
- No new dependency or MCP server without asking.
- Do not describe a loop as successful if the final check did not run.

## Checkpoint

After each iteration, append to `artifacts/loop.md` (for recovery, not for the
commit):

```
ITERATION: <n>
HYPOTHESIS: <one line>
CHANGE: <files>
RESULT: <pass/fail + key output line>
NEXT: <one line or STOP: reason>
```

If the loop gets long, also keep a short "ruled out" list so you do not repeat
dead ends.

## Reporting

End with:

```
STATUS: <done | stopped | blocked>
CHECK: <the command used, and whether it was given or inferred>
EVIDENCE: <final check output, one line>
ITERATIONS: <n>
NOT DONE: <what a reviewer would expect that you did not do>
```
