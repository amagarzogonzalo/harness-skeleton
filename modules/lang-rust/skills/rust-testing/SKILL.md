---
name: rust-testing
description: Rust test patterns. Trigger when adding unit, integration, doc, property, or async tests, or when a test is flaky or slow.
---

# Rust testing

## Layout

```
src/lib.rs            # unit tests in #[cfg(test)] mod tests
tests/integration.rs  # public API, one binary per file
benches/              # criterion, not part of the gate
```

- Unit tests live beside the code and may access private items.
- Integration tests use only the public API, the way a user does.
- Doc tests are compiled and run by `cargo test`; keep examples short and real.

## Commands

```bash
cargo test --all-features
cargo test --all-features test_name -- --nocapture
cargo test --doc
cargo nextest run --all-features      # optional, faster and better output
cargo llvm-cov --all-features         # optional coverage
```

## Assertions

```rust
assert_eq!(parse("1"), Ok(1));
assert!(matches!(parse("-"), Err(ParseError::Empty)));
```

- Assert the error variant, not only `is_err()`.
- `#[should_panic(expected = "...")]` must include the expected message.
- Do not use `unwrap()` in a test to hide a useful failure; `expect("why")` is
  better, and a `Result`-returning test is better still.

## Properties and fuzzing

- `proptest!` for pure functions with a wide input space: parsers, codecs,
  arithmetic, normalization.
- Keep the input strategy small and the test deterministic with a seed.
- `cargo fuzz` for parsers and unsafe boundaries; run it in a nightly job, not
  the pre-commit gate.

## Async

- Use `#[tokio::test]` (or the project's runtime) and `tokio::time::pause` for
  time-dependent behavior.
- No real sleeps. No real network. Use a local fake or a trait boundary.
- A spawned task must be joined or aborted before the test ends.

## Stop conditions

- A test that passes before the change is wrong.
- A test that needs a global mutable singleton is at the wrong level.
- A test slower than 100 ms is a candidate for the integration/nightly tier.
- A flaky test is a bug; do not add a retry loop.
