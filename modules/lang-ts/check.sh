#!/usr/bin/env bash
# Offline TypeScript gate. Uses the project's own scripts when they exist, then
# falls back to tsc for type checking. Detects the package manager from its
# lockfile; never guesses npm when the project uses pnpm.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if [ ! -f package.json ]; then
  echo "lang-ts: no package.json" >&2
  exit 1
fi

pm="npm"
if [ -f pnpm-lock.yaml ]; then
  pm="pnpm"
elif [ -f yarn.lock ]; then
  pm="yarn"
elif [ -f bun.lockb ] || [ -f bun.lock ]; then
  pm="bun"
fi

if ! command -v "$pm" >/dev/null 2>&1; then
  echo "lang-ts: $pm is not on PATH" >&2
  exit 1
fi

has_script() {
  node -e '
    const p = require("./package.json");
    process.exit(p.scripts && p.scripts[process.argv[1]] ? 0 : 1);
  ' "$1"
}

echo "lang-ts: package manager $pm"

if has_script lint; then
  echo "lang-ts: $pm run lint"
  "$pm" run lint
else
  echo "lang-ts: no lint script (add one to package.json)"
fi

if has_script typecheck; then
  echo "lang-ts: $pm run typecheck"
  "$pm" run typecheck
elif [ -f tsconfig.json ] || [ -f tsconfig.strict.json ]; then
  echo "lang-ts: tsc --noEmit"
  case "$pm" in
    npm)  npx --no-install tsc --noEmit ;;
    pnpm) pnpm exec tsc --noEmit ;;
    yarn) yarn tsc --noEmit ;;
    bun)  bunx tsc --noEmit ;;
  esac
else
  echo "lang-ts: no typecheck script and no tsconfig"
fi

if has_script test; then
  echo "lang-ts: $pm test"
  "$pm" test
else
  echo "lang-ts: no test script (add one to package.json)"
fi
