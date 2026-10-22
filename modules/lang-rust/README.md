# lang-rust

Rust review, unsafe audit, and an offline fmt/clippy/test gate.

## Enable

```bash
make enable M=lang-rust
```

Adds `rust-reviewer`, `rust-unsafe-reviewer`, `rust-testing`, and `rust-unsafe`.
Both agents are read-only and mapped to the `review` role.

The unwrap toast is opt-in:

```bash
uv run python bin/modules.py enable lang-rust --with-hooks
```

## What the check runs

```bash
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
```

`cargo test` includes doc tests. The gate is offline and deterministic.

## What it does not do

- `cargo audit`, `cargo deny`, `cargo outdated`: network. Run `audit.sh` or the
  scheduled CI job.
- Miri: nightly and slow. Run it on the unsafe surface, not the whole tree.
- Mutation testing: nightly. `cargo-mutants` is useful, not a pre-commit step.

## Files

| File | Purpose |
|---|---|
| `agent/rust-reviewer.md` | Ownership, errors, async, API, performance |
| `agent/rust-unsafe-reviewer.md` | Soundness, aliasing, FFI, unsafe impls |
| `skills/rust-testing/SKILL.md` | Unit/integration/doc/property/async tests |
| `skills/rust-unsafe/SKILL.md` | Safety contract and checklist |
| `hooks/no-unwrap.js` | Warning toast for unwrap/expect (opt-in) |
| `check.sh` | fmt + clippy + test |
| `audit.sh` | audit/deny/outdated (network) |
| `rustfmt.toml.example` | Formatter config |
| `clippy.toml.example` | Lint config |
| `deny.toml.example` | License/advisory/source policy |
| `CI.fragment.yml` | CI job, pin the actions to SHAs |
