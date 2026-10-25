.PHONY: help install setup safe auto full agents-list test lint types context agents check \
        profile profiles evals evals-live evals-accept sessions \
        modules enable disable modules-check skill-sync \
        install-hooks \
        compress-on compress-off compress-savings compress-help

SKILL_SOURCE ?= ../projects/research-orchestration-agents/skills/deep-research

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22

install:            ## install deps into .venv
	uv sync --no-install-project --all-extras

setup:              ## bootstrap: check tools, install deps, run offline checks
	uv run python bin/bootstrap.py

safe:               ## launch opencode with project permissions (prompts)
	uv run python bin/opencode_mode.py safe

auto:               ## launch opencode with no prompts; explicit denies still apply
	uv run python bin/opencode_mode.py auto

full:               ## launch opencode with full permissions; dangerous
	uv run python bin/opencode_mode.py full

agents-list:        ## list the agents OpenCode detects in this project
	opencode agent list

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

check: lint types agents context test evals modules-check   ## everything. This is the gate.
	uv run python bin/gate_marker.py write
	@echo green

# ---- modules (opt-in catalog; core is the root) ---------------------------
modules:            ## list the module catalog and detected stacks
	uv run python bin/modules.py list

enable:             ## enable a module: make enable M=lang-python
	@test -n "$(M)" || { echo "usage: make enable M=<module>"; exit 1; }
	uv run python bin/modules.py enable $(M)

disable:            ## disable a module: make disable M=lang-python
	@test -n "$(M)" || { echo "usage: make disable M=<module>"; exit 1; }
	uv run python bin/modules.py disable $(M)

modules-check:      ## run check.sh for every enabled module
	uv run python bin/check_modules.py

skill-sync:         ## refresh the vendored deep-research skill from its canonical repo
	uv run python bin/sync_skill.py --module deep-research --source $(SKILL_SOURCE)

install-hooks:      ## point git at .githooks/ for this clone
	git config core.hooksPath .githooks
	@echo "hooks installed: .githooks/pre-commit"

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
