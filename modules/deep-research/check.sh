#!/usr/bin/env bash
# Offline integrity check for the vendored deep-research skill.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

PY=python
command -v python >/dev/null 2>&1 || PY=python3
exec "$PY" modules/deep-research/check.py
