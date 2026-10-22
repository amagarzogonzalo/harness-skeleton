#!/usr/bin/env bash
# Offline Python checks. Core already runs ruff, mypy, and pytest; this adds
# bandit, which the harness does not install by default.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if ! command -v bandit >/dev/null 2>&1; then
  echo "lang-python: bandit not installed; skipping (uv add --dev bandit)"
  exit 0
fi

target="."
[ -d src ] && target="src"

echo "lang-python: bandit -ll -r $target"
bandit -q -ll -r "$target"
