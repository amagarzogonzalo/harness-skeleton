---
name: typescript-testing
description: TypeScript test patterns. Trigger when adding or fixing TS tests, async tests, type-level tests, mocks, or coverage.
---

# TypeScript testing

Use the project's runner. Do not add Vitest to a Jest project, or vice versa.

## Commands

```bash
npm test
npm test -- src/foo.test.ts
npm test -- -t "name"
npm run typecheck
```

With pnpm/yarn/bun, substitute the package manager; do not mix lockfiles.

## Behavior, not implementation

```ts
it("rejects an expired token", async () => {
  const result = await verify("expired-token");
  expect(result).toEqual({ ok: false, reason: "expired" });
});
```

- Query by role/label/text in component tests, not by class or test id unless
  there is no accessible alternative.
- Assert the observable result, not how many times a private function ran.
- Do not mock the module under test. Mock the network, clock, and filesystem at
  the boundary (MSW, fake timers, `memfs`).

## Async

- Always `await` the assertion (`await screen.findBy...`, `await expect(...).rejects`).
- Do not use `setTimeout` in a test; use fake timers or a deterministic promise.
- Restore timers and mocks in `afterEach`.
- A test that passes only with `--runInBand` is hiding shared state.

## Type tests

When a type is the contract, test the type:

```ts
import { expectTypeOf } from "vitest";

expectTypeOf(parse("1")).toEqualTypeOf<number>();
```

`tsd` or `expect-type` works too. Type tests belong beside the unit tests and run
under `tsc`, not only under the test runner.

## Network

- MSW or a local fake server; never a real third-party API in a unit test.
- Contract tests against a recorded fixture are fine; record them explicitly and
  keep them small.
- A test that needs an API key is an integration test; mark it and keep it out
  of the default gate.

## Coverage

- Coverage is a smoke detector. Do not write assertion-free tests to raise it.
- Snapshot tests are useful for stable serialization, not for whole components.
  A snapshot nobody reads is not a test.
- Mutation testing (Stryker) is a nightly tool, not a pre-commit step.

## Stop conditions

- The test passes before the change: the test is wrong.
- The test needs six mocks: move it to the boundary.
- The test is flaky: fix the shared state or the clock; do not retry.
