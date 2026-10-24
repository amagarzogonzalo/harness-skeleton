---
name: tdd
description: Test-driven development: write a failing test first, make the smallest change to pass it, then refactor. Use when adding logic, fixing a bug, or changing a testable contract. Use `/tdd`.
metadata:
  opencode/slash: "true"
---

# Test-driven development

One behavior per cycle. Do not write production code until a test fails for the
right reason.

## RED

1. Write the smallest test that states the behavior. Name it after the behavior,
   not the function.
2. Run it. It must fail. If it passes, the test is wrong or the behavior already
   exists; stop and investigate.
3. Read the failure. It must fail because the behavior is missing, not because of
   a typo, import error, or fixture mistake.

```bash
uv run pytest tests/test_<area>.py::<test> -q
```

## GREEN

4. Write the minimum production code that makes that one test pass. Do not add
   the next feature, the abstraction, or the edge case.
5. Run the test again. Then run the surrounding tests.

```bash
uv run pytest tests/test_<area>.py -q
```

## REFACTOR

6. Remove duplication and improve names, with the test green.
7. Run the full gate. If it is red, the refactor changed behavior; revert it.

```bash
make check
```

## Test quality

- Assert on observable behavior, not implementation details.
- One logical assertion per test. Multiple `assert`s are fine if they describe
  one outcome.
- No test without an assertion.
- Do not mock the thing under test. Mock the network, clock, and filesystem.
  Prefer `tmp_path`, `monkeypatch`, and a fake at the boundary.
- No `sleep` in tests. Use fake clocks, polling with a deadline, or an event.
- A flaky test is a bug. Fix it or delete it; do not retry it.
- If a test cannot fail, it is documentation, not a test. Rewrite it.

## Stop conditions

- The test passes before the code change: the test is wrong or the behavior
  exists. Stop.
- You cannot make the test fail for the right reason: the test is at the wrong
  level. Move it down or up, then restart the cycle.
- Three cycles without a green test: stop, write down what you learned, and
  narrow the behavior.

## Optional

Mutation testing and property-based testing are nightly/CI tools, not part of
the edit loop. If the project has them, run them against the changed module, not
the whole tree.
