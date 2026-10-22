---
name: test-review
description: Procedure for reviewing a test diff. Trigger when a PR adds or changes tests, a bug fix has no regression test, or a flaky test is reported.
---

# Test review

## Procedure

1. **Read the production diff first.** List each changed behavior. If the tests
   are reviewed without the behavior, the missing case is invisible.
2. **Map behavior to test.** For each changed branch, name the test that fails
   if the branch is removed. No name means no coverage.
3. **Check the assertion.** Does it fail for the wrong implementation? Would it
   pass if the function returned a plausible wrong value?
4. **Check the level.** A unit test with six mocks is testing the mocks. Move it
   to the boundary or make the dependency fakeable.
5. **Check determinism.** No real clock, network, random seed, shared state, or
   test-order dependence.
6. **Check the failure message.** A failing test should say what was expected
   and what happened, not just `AssertionError`.

## Missing-case prompts

- Empty, one, many, max, over max.
- `None`/`undefined`/`null`, empty string, zero, negative.
- Unauthorized, forbidden, not found, conflict, timeout, partial failure.
- Retry after success, retry after failure, duplicate request.
- Unicode, whitespace, path separators, very long input.
- Concurrent calls against shared state.

## Verdict

```
COVERED:    <behavior> -> <test>
UNCOVERED:  <behavior> -> <test to add>
WEAK:       <test> -> <why it cannot fail>
FLAKY:      <test> -> <source of nondeterminism>
```

`UNCOVERED` for a changed behavior is blocking. `LOW` style issues are not
findings; do not pad the review.
