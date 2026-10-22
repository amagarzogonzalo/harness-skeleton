#!/usr/bin/env bash
# Network-dependent Rust audit. Keep it out of `make check` and pre-commit.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

run() {
  if command -v "$1" >/dev/null 2>&1; then
    shift
    "$@"
  else
    echo "skip: $1 not installed"
  fi
}

run cargo-audit cargo audit
run cargo-deny cargo deny check
run cargo-outdated cargo outdated --root-deps-only
