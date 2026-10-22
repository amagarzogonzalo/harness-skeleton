#!/usr/bin/env bash
# Network-dependent Node audit. Keep it out of `make check` and pre-commit.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

pm="npm"
if [ -f pnpm-lock.yaml ]; then pm="pnpm"; elif [ -f yarn.lock ]; then pm="yarn"; elif [ -f bun.lockb ] || [ -f bun.lock ]; then pm="bun"; fi

case "$pm" in
  npm)  npm audit --omit=dev ;;
  pnpm) pnpm audit --prod ;;
  yarn) yarn npm audit --environment production ;;
  bun)  bun audit ;;
esac

if command -v osv-scanner >/dev/null 2>&1; then
  osv-scanner --lockfile package-lock.json
else
  echo "osv-scanner not installed (optional, cross-ecosystem)"
fi
