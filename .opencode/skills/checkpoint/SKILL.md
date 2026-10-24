---
name: checkpoint
description: Write a compact recovery state before compaction, a handoff, or a long pause, so a fresh session can continue. Use `/checkpoint`.
metadata:
  opencode/slash: "true"
---

# Checkpoint

A checkpoint lets a fresh session continue without replaying the conversation.
Write facts, not narrative. Keep it under 40 lines.

## When

- Before the context window is compacted.
- After a milestone (a green gate, a merged sub-task, a decision).
- Before handing work to another person or agent.
- When a loop stops without finishing.

## Format

```markdown
# Checkpoint: <task>

## Goal
<one sentence, observable end state>

## Done
- <what is true now, with file:line or command evidence>

## In progress
- <the one thing being changed, and its current state>

## Next
1. <the next concrete action>
2. <the action after that>

## Decisions
- <decision> — <why> — <what would reverse it>

## Open questions
- <question> — <who or what can answer it>

## Gate
- `make check`: <green | red at X | not run>
- `artifacts/gate.json`: <head, timestamp>

## Files touched
- <path> — <what changed>

## Do not
- <approaches already ruled out, and why>
```

## Rules

- Include exact commands and their result, not "tests pass".
- Mark uncertain claims as `UNVERIFIED`. Do not present a guess as a fact.
- Do not copy large diffs. Reference paths.
- Do not include secrets, tokens, or customer data.
- If the checkpoint is for compaction, put the goal and next action first; that
  is what the next context needs most.
- Store it at `artifacts/checkpoint.md` (gitignored) unless the user asks for a
  committed handoff.
