.PHONY: help install test lint types context agents check \
        profile profiles evals evals-live evals-accept sessions \
        compress-on compress-off compress-savings compress-help

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22

install:            ## install deps into .venv
	uv sync --no-install-project --all-extras

# ---- the gate -------------------------------------------------------------
# `--no-install-project`: the harness is tooling, not a package. This installs the
# dependencies (openai, pyyaml, tiktoken) and dev extras (ruff, mypy, pytest)
# without trying to build the skeleton as a wheel.
# test/types guard on directory existence so this template is green out of the
# box, and the same targets work once a real project supplies src/ and tests/.
test:               ## unit tests, no network (skips if no tests/)
	@if [ -d tests ]; then uv run pytest tests/ -q; else echo "no tests/ — skipping"; fi

lint:               ## formatting + style
	uv run ruff check . && uv run ruff format --check .

types:              ## static types (skips if no src/)
	@if [ -d src ]; then uv run mypy src/; else echo "no src/ — skipping"; fi

agents:             ## structural checks on AGENTS.md
	uv run python bin/lint_agents.py

context:            ## what the always-on prompt costs, enforced
	uv run python bin/context_budget.py

check: lint types agents context test evals   ## everything. This is the gate.
	@echo green

# ---- models ---------------------------------------------------------------
profiles:           ## list model profiles
	uv run python bin/apply_profile.py --list

profile:            ## switch profile:  make profile P=frontier
	uv run python bin/apply_profile.py $(P)

sessions:           ## cost per model over the last 30 days
	uv run python bin/sessions.py

# ---- evals (optional module; delete evals/ if not LLM-driven) -------------
evals:              ## offline replay, free, deterministic
	uv run python evals/runner.py

evals-live:         ## live calls, re-records cassettes. Costs money.
	EVAL_MODE=record uv run python evals/runner.py --record

evals-accept:       ## adopt current digests as the new baseline (HUMAN ONLY)
	uv run python evals/runner.py --accept

# ---- context compression (optional) --------------------------------------
compress-on:        ## start the local compression proxy
	./bin/compress.sh on
compress-off:       ## stop it and restore config
	./bin/compress.sh off
compress-savings:   ## measured reduction on your own traffic
	./bin/compress.sh savings
compress-help:
	./bin/compress.sh help
