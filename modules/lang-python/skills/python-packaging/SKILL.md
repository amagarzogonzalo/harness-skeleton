---
name: python-packaging
description: Python packaging and dependency hygiene. Trigger when editing pyproject.toml, adding a dependency, building a wheel, or changing the supported Python version.
---

# Python packaging

## Layout

Prefer a `src/` layout:

```
pyproject.toml
src/<package>/__init__.py
tests/
```

A flat layout lets `import <package>` resolve to the working directory instead
of the installed package, which hides packaging bugs.

## pyproject.toml

```toml
[project]
name = "example"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["httpx>=0.27,<1"]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.6", "mypy>=1.11"]

[project.scripts]
example = "example.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- Pin the **lower** bound and, for libraries, a practical upper bound. An
  unbounded dependency is a future break.
- Runtime dependencies go in `dependencies`; test/lint/build tools go in an
  optional `dev` group.
- `requires-python` must match the CI matrix and the syntax you use.
- Do not add a dependency for one function. Check the standard library first.
- Every dependency is a supply-chain surface: check the maintainer, the release
  history, install scripts, and the license.

## Lockfile

- Commit the lockfile (`uv.lock`, `poetry.lock`, `requirements.txt` with hashes).
- After changing dependencies, regenerate it and review the diff.
- CI installs from the lockfile, not from an unpinned resolve.

```bash
uv lock
uv sync --frozen --no-install-project
```

## Build and verify

```bash
uv build
uv run twine check dist/*
```

Install the wheel in a clean environment and run the entry point. A package that
works only from the source tree is not packaged.

## Versioning

- Follow the project's existing scheme; do not invent a new one.
- A breaking change to a public import, CLI flag, or serialized format is a
  major version (or the project's equivalent).
- Do not publish from an agent session. Build, verify, and hand the artifact to
  a human.
