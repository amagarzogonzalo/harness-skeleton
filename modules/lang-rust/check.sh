#!/usr/bin/env bash
# Offline Rust gate: format, lints, tests (including doc tests).
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if ! command -v cargo >/dev/null 2>&1; then
  echo "lang-rust: cargo not found on PATH" >&2
  exit 1
fi

echo "lang-rust: cargo fmt --check"
cargo fmt --all -- --check

echo "lang-rust: cargo clippy -D warnings"
cargo clippy --all-targets --all-features -- -D warnings

echo "lang-rust: cargo test"
cargo test --all-features
