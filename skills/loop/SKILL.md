---
name: loop
description: Bounded autonomous iteration for a multi-step task with a checkable stop condition. Trigger when a task needs repeated edit-run-inspect cycles, not for a one-shot change.
---

# Bounded loop

A loop is allowed only when "done" is a command, not a feeling.

## Before the first iteration

Write four lines:

```
GOAL:    <observable end state>
CHECK:   <exact command that proves it>
CAP:     <max iterations, default 10>
EVIDENCE:<where each iteration's result is recorded — artifacts/loop.md>
```

If you cannot name the check, you are not ready to loop. Plan instead.

## Each iteration

1. State the one hypothesis you are testing.
2. Make the smallest change that tests it.
3. Run the check. Record the command and the result verbatim.
4. Decide: continue, change approach, or stop.

Never run two unrelated changes in one iteration; you will not know which one
moved the result.

## Stop matrix

| Condition | Action |
|---|---|
| Check passes | Stop. Run `make check` once, then report. |
| Same failure twice | Stop. The hypothesis is wrong, not the code. |
| No measurable progress in 2 iterations | Stop. Write down what you ruled out. |
| Check cannot run (missing tool, permission) | Stop. Report the blocker. |
| A change would touch a hard rule or a budget | Stop. Ask. |
| Context is more than ~60% full | Checkpoint, then stop or split the task. |
| You are about to add a dependency | Stop. Ask. |

## Hard caps

- 10 iterations unless the user sets a different cap.
- 2 consecutive identical failures.
- No raising a test threshold, coverage target, or context budget to pass.
- No deleting, skipping, or weakening a test to pass.
- No `--no-verify`, no force-push, no rewriting history.

## Checkpoint

After every iteration, append to `artifacts/loop.md`:

```
ITERATION: <n>
HYPOTHESIS: <one line>
CHANGE: <files>
RESULT: <pass/fail + key output line>
NEXT: <one line or STOP: reason>
```

`artifacts/` is gitignored. The checkpoint is for recovery, not for the commit.

## Reporting

End with:

```
STATUS: <done | stopped | blocked>
EVIDENCE: <final check output, one line>
ITERATIONS: <n>
NOT DONE: <what a reviewer would expect that you did not do>
```

Do not describe a loop as successful if the final check did not run.
