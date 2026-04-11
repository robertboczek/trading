# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

This is a Python trading project. The repository is in early setup — no source code, build configuration, or test infrastructure exists yet.

## Setup

No build or dependency configuration has been established. When adding Python packaging, consider using `pyproject.toml` with a tool like `uv`, `poetry`, or standard `setuptools`.

## Testing

No test framework is configured. Pytest is a common choice for Python projects:

```bash
pytest                  # run all tests
pytest tests/path/to/test_file.py::test_name  # run a single test
```

## Linting

No linting configuration exists yet. `ruff` is a fast all-in-one linter/formatter for Python:

```bash
ruff check .
ruff format .
```
