#!/usr/bin/env bash
# Network-dependent Python audit. Never run this from `make check` or a
# pre-commit hook: a gate that needs the network is a gate that fails offline.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "== pip-audit =="
if command -v pip-audit >/dev/null 2>&1; then
  pip-audit --skip-editable
else
  echo "pip-audit not installed (uv add --dev pip-audit)"
fi

echo "== bandit (all severities) =="
if command -v bandit >/dev/null 2>&1; then
  bandit -r "${1:-.}"
else
  echo "bandit not installed (uv add --dev bandit)"
fi
