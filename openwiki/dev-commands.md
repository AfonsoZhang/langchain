---
type: "Developer Tools & Commands"
title: "Development Commands and Workflow"
description: "CLI reference and developer workflow: building packages, running tests locally, linting, type checking, CI simulation, and common troubleshooting patterns."
tags: [development, build, testing, linting, typing, uv, make, pre-commit, workflow]
verified:
  - by: openwiki/0.5.0
    at: 2026-10-07T08:30:45.453Z
sources:
  - id: openwiki-source-4d1645cb6317345817452838
    resource: repo://.pre-commit-config.yaml
  - id: openwiki-source-8037e2358a2c4f9b2c722a11
    resource: repo://AGENTS.md
  - id: openwiki-source-8f1875229ad4a704c8e20a06
    resource: repo://libs/core/Makefile
  - id: openwiki-source-3486a94e6eb23a78271a5bfb
    resource: repo://libs/core/pyproject.toml
  - id: openwiki-source-7c96a74af67942d40559bf7d
    resource: repo://libs/langchain_v1/Makefile
  - id: openwiki-source-f708a9db48bfcf1b154e4708
    resource: repo://libs/langchain/Makefile
  - id: openwiki-source-49fbcc45434b619b68220bf9
    resource: repo://libs/Makefile
  - id: openwiki-source-a6e669bb11f217c6fbd06670
    resource: repo://libs/partners/anthropic/Makefile
generated: { by: "openwiki/0.5.0", at: "2026-10-07T08:30:45.453Z" }
---

## Overview

The LangChain Python monorepo uses `uv` for dependency management, `make` for task automation, and `ruff`/`mypy` for code quality. This page provides a comprehensive reference for common development commands, testing workflows, linting setup, CI simulation locally, and troubleshooting patterns.

Each package in `libs/` maintains its own `pyproject.toml`, `uv.lock`, and `Makefile`. There is no workspace-level configuration at the repo root—always navigate to the package directory before running commands. For example: `cd libs/langchain_v1` or `cd libs/core`.

## Initial Setup

### Install Dependencies

Each package in `libs/` has its own `pyproject.toml` and `uv.lock`. Before running tests or making changes, set up dependencies:

```bash
# Install all dependency groups (lint, typing, test, dev)
uv sync --all-groups

# Or install only a specific group
uv sync --group test
uv sync --group lint
```

The `--all-groups` flag ensures you have tools for linting, type checking, and testing. See the [Contributing Guide in AGENTS.md](repo://AGENTS.md) for detailed development conventions and PR guidelines.

### Pre-Commit Setup

The repository uses pre-commit hooks to enforce code quality on commit. Install and configure them once:

```bash
# Install pre-commit hooks (run from repo root)
pre-commit install
```

Pre-commit runs automatically on staged files before each commit. To manually trigger or simulate hooks:

```bash
# Run all hooks on all files (useful for CI simulation)
pre-commit run --all-files

# Run hooks for a specific package
pre-commit run core --all-files

# Dry run: show what would happen without making changes
pre-commit run --all-files --dry-run
```

## Pre-Commit Hooks

The `.pre-commit-config.yaml` defines hooks that enforce code quality before commits:

- **Standard validation**: YAML/TOML syntax checking (`check-yaml`, `check-toml`), proper file endings (`end-of-file-fixer`), and no trailing whitespace removal
- **Text normalization**: Fix curly quotes (`fix-smartquotes`) and replace non-breaking spaces with regular spaces (`fix-spaces`)
- **Per-package format and lint**: Each package in `libs/` (core, langchain, standard-tests, text-splitters, and partners/*) automatically runs `make format lint` on changed files
- **Version consistency checks**: Hooks verify that `pyproject.toml` versions match source code version fields for `langchain-core`, `langchain_v1`, and partner packages (anthropic, chroma, deepseek, exa, fireworks, groq, huggingface, mistralai, nomic, ollama, openai, qdrant)
- **Branch protection**: Prevent commits directly to `master` branch

These hooks automatically prevent commits that fail linting or have formatting issues. They use the same Makefiles documented below. The pre-commit configuration can be inspected locally by running `pre-commit run --all-files` to simulate CI behavior before pushing.

## Testing Commands

### Run All Unit Tests

```bash
# From a package directory (always cd first)
cd libs/core  # or libs/langchain_v1, etc.
make test
```

Unit tests live in `tests/unit_tests/` and run with socket restrictions (`--disable-socket --allow-unix-socket`) to prevent accidental network calls. The test target uses `pytest` with:
- **Parallelization**: `-n auto` via `pytest-xdist` to run tests concurrently
- **Environment isolation**: Unsets `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGSMITH_*` to avoid interference from LangSmith configuration
- **Benchmark disabling**: `--benchmark-disable` to skip profiling by default

**Note for langchain_v1**: The package uses Docker services (PostgreSQL, Redis) managed automatically by the Makefile. The `make test` target starts services before running tests and stops them afterward, handling exit codes properly.

### Run a Specific Test File or Directory

```bash
# Using make (default TEST_FILE=tests/unit_tests/)
make test TEST_FILE=tests/unit_tests/agents/test_agent.py

# Test a directory
make test TEST_FILE=tests/unit_tests/agents/

# With extra pytest options (verbose, show print statements, etc.)
make test TEST_FILE=tests/unit_tests/agents PYTEST_EXTRA="-vv -s"

# Using uv directly (useful when not in a package directory)
cd libs/core
uv run --group test pytest tests/unit_tests/agents/test_agent.py -vv
```

**Pytest fixtures and debugging:**
- Use `-vv` for verbose output showing each test and its result
- Use `-s` to capture and display print statements from tests
- Use `-k <pattern>` to run tests matching a name pattern: `pytest -k "test_agent" tests/`
- Use `--tb=short` or `--tb=long` to control traceback detail on failure
- Use `--lf` (last failed) to re-run only tests that failed in the previous run
- Use `--ff` (failed first) to run failed tests first, then other tests
- Use `--pdb` to drop into debugger on test failure
- Use `@pytest.fixture` in test files for setup/teardown and `@pytest.mark.parametrize` for parameterized tests

### Integration Tests

Integration tests live in `tests/integration_tests/` and require network access, API keys, and external services. Run them separately from unit tests:

```bash
# From a package directory
make integration_tests
```

Integration tests differ from unit tests:
- **Unit tests** (`tests/unit_tests/`): No network calls, socket restrictions enabled, fast feedback
- **Integration tests** (`tests/integration_tests/`): Network calls allowed, require API keys (e.g., `OPENAI_API_KEY`), test against real services

For packages like `langchain_v1` that use Docker services:

```bash
cd libs/langchain_v1

# Full test suite (starts Docker services, runs unit + extended tests, stops services)
make test

# Fast variant with in-memory services instead of Docker
make test_fast

# Only extended tests (marked with @pytest.mark.extended)
make extended_tests

# Manual service management
make start_services  # Start PostgreSQL and Redis
make stop_services   # Stop services
```

The Docker compose files are in `tests/unit_tests/agents/compose-postgres.yml` and `tests/unit_tests/agents/compose-redis.yml`.

### Test in Watch Mode

Auto-re-run tests as you edit code for rapid feedback during development:

```bash
# Watch and re-run all unit tests
make test_watch

# Watch and re-run extended tests (for langchain_v1)
make test_watch_extended  # langchain_v1 only
```

Watch mode uses `pytest-watcher` (the `ptw` command) and:
- Automatically re-runs affected tests when files change
- Updates snapshots automatically (`--snapshot-update`)
- Displays verbose output (`-vv`)
- For `langchain_v1`, it starts/stops Docker services automatically
- Stops on first failure (`-x`) to avoid test output spam

### Coverage Reports

Generate code coverage reports to identify untested code:

```bash
# Standard coverage report for all unit tests
make coverage

# Middleware and agent-specific coverage (langchain_v1 only)
make coverage_agents

# View detailed results
# - XML format: coverage.xml (for CI integration)
# - Terminal format: shows coverage % per module and uncovered lines
```

Coverage reports are useful for:
- Finding untested code paths
- Tracking coverage trends over time
- Understanding which files need more test attention
- XML reports integrate with CI/CD systems

## Linting and Formatting

### Run Full Linting Suite

```bash
# Run all linting and type checks (from package directory)
make lint
```

This runs three checks in sequence:
1. **Import validation** (`./scripts/lint_imports.sh`): Custom checks on import statements
2. **Ruff check**: Linter for logical errors, naming conventions, import sorting, unused variables, and code smells (all rules enabled)
3. **Ruff format --diff**: Format checking in diff mode (shows what would change, does not modify files)
4. **Mypy**: Static type checking with strict mode enabled

The lint target checks all Python files (`.py`) and Jupyter notebooks (`.ipynb`).

### Format Code

```bash
# Auto-fix all formatting and logical issues
make format
```

This applies two formatters in order:
1. **Ruff format**: Reformats code (whitespace, line breaks, docstring formatting)
2. **Ruff check --fix**: Auto-fixes logical issues (sorts imports, removes unused variables, fixes obvious errors)

After running `make format`, staged files are ready to commit if linting passes.

### Ruff-Only Commands

For faster iteration, format and linter can be run separately or individually:

```bash
# Check linting without fixing
ruff check .

# Check formatting without modifying
ruff format . --diff

# Fix only logical issues (imports, unused vars, etc.)
ruff check . --fix

# Fix only formatting (does not fix logical errors)
ruff format .

# Check a specific file
ruff check libs/core/langchain_core/agent.py
ruff format libs/core/langchain_core/agent.py --diff
```

Ruff processes Python and Jupyter notebooks. Run from within a package directory.

### Linting Changed Files Only

For faster feedback during development, lint only files changed in the current branch:

```bash
# Lint only changed files against master
make lint_diff
make format_diff

# This uses git diff to identify changed files
```

### Type Checking

Full static type checking with mypy (strict mode):

```bash
# Type check all files
make type

# Type check specific file or directory
mypy libs/core/langchain_core/agent.py

# Type check only tests (uses separate cache)
make lint_tests
```

Type checking can be slow for large packages. Benefits include:
- Catches incorrect argument types before runtime
- Ensures type hints are present on all public functions
- Detects incomplete type annotations
- Mypy is configured with `strict = true`, requiring comprehensive type coverage

## Developing a Single Package

To focus on a specific package in the monorepo:

```bash
# Navigate to the package (required—no workspace-level config)
cd libs/langchain_v1

# Install all dependencies (test, lint, typing, dev groups)
uv sync --all-groups

# Or install only specific groups
uv sync --group test
uv sync --group lint

# Run all unit tests with default settings
make test

# Run tests in a specific file with extra options
make test TEST_FILE=tests/unit_tests/agents/test_create_agent.py PYTEST_EXTRA="-vv -s"

# Format code
make format

# Lint and type check
make lint
make type

# View all available targets
make help
```

Each package under `libs/` has its own `Makefile`, `pyproject.toml`, and `uv.lock` with consistent targets. The monorepo root `/libs/Makefile` provides cross-package commands for dependency management (see "Lock File Management" section below).

**Package-specific targets** (check `make help` in each package):
- `langchain_v1`: `test_fast`, `coverage_agents`, `start_services`, `stop_services`, `test_watch_extended`, `extended_tests`
- `core`: `check_imports`, `test_profile`, `benchmark`
- `partners/*`: `integration_tests` (with API key requirements)

## Lock File Management

The `uv.lock` file in each package pins exact dependency versions for reproducible builds across all environments. Lock files are generated from `pyproject.toml` dependency declarations.

### When to Update Lock Files

Update locks when you add, remove, or change dependency versions in `pyproject.toml`:

```bash
# From a package directory, regenerate lock
cd libs/langchain_v1
uv lock

# Or regenerate all core package locks from libs/
cd libs
make lock

# Verify all locks are up-to-date (useful before committing)
uv lock --check   # Single package
cd libs && make check-lock  # All packages
```

### Lock File Workflow

1. **Regular development**: Use `uv sync --all-groups` without modifying locks
   - `UV_FROZEN = true` in Makefiles prevents accidental lock changes
   - Dependencies stay pinned to versions in `uv.lock`

2. **Adding a dependency**:
   ```bash
   # Edit pyproject.toml to add a dependency
   # Then regenerate lock
   cd libs/<package>
   uv lock
   # Commit both pyproject.toml and uv.lock
   ```

3. **Updating dependencies** (maintenance):
   ```bash
   # Update all dependencies (may change uv.lock significantly)
   uv lock --upgrade
   # Review changes and test thoroughly
   make test
   ```

Lock files ensure:
- Reproducible builds on all machines (CI, laptops, production)
- No silent version conflicts when multiple developers use different environments
- Explicit visibility into dependency versions used
- Pre-commit hooks prevent accidental lock changes during regular development

## Make Commands Reference

All packages in `libs/` follow the same Makefile structure with consistent targets. Use `make help` in any package directory to see all available targets.

### Core Commands (Available in All Packages)

| Command | Purpose |
|---------|---------|
| `make test` | Run all unit tests with pytest and parallelization |
| `make test TEST_FILE=<path>` | Run tests in a specific file or directory |
| `make test_watch` | Run tests in watch mode (auto-rerun on file changes) |
| `make integration_tests` | Run integration tests (requires API keys and network access) |
| `make extended_tests` | Run only tests marked with `@pytest.mark.extended` |
| `make lint` | Run import validation + ruff check + ruff format --diff + mypy |
| `make lint_diff` | Lint only files changed vs. master branch |
| `make format` | Apply ruff format and ruff check --fix |
| `make format_diff` | Format only files changed vs. master branch |
| `make type` | Run mypy type checking on all files |
| `make coverage` | Run unit tests and generate coverage report (xml + terminal) |
| `make help` | Display all available targets for that package |

### Package-Specific Commands

**langchain_v1** (active package with full agent support):
- `make test_fast` – Run tests with in-memory services instead of Docker
- `make coverage_agents` – Coverage report for agents middleware only
- `make start_services` – Start PostgreSQL and Redis Docker containers
- `make stop_services` – Stop Docker services
- `make test_watch_extended` – Watch mode for extended tests only
- `make benchmark` – Run create_agent performance benchmarks

**core** (base abstractions):
- `make check_imports` – Validate import structure
- `make test_profile` – Run tests with performance profiling (svg output)
- `make benchmark` – Run codspeed benchmarks

**partners/** (third-party integrations):
- `make integration_tests` – Run tests against real external APIs (requires API keys)

## Common Workflows

### Pre-Commit Development Checklist

Before pushing code, run these steps to simulate CI locally:

```bash
# From the package directory where you made changes
cd libs/langchain_v1

# 1. Ensure dependencies are installed
uv sync --all-groups

# 2. Format code (fixes common issues automatically)
make format

# 3. Run tests (catches logic errors)
make test

# 4. Check linting and types (catches style and type errors)
make lint

# 5. Simulate pre-commit hooks (optional—will run automatically on commit)
pre-commit run --all-files

# 6. Commit changes
git add .
git commit -m "feat(langchain_v1): describe your change"
```

The pre-commit hooks will then automatically run and prevent the commit if any checks fail.

### Quick Iteration During Development

For rapid feedback while editing:

```bash
# Terminal 1: Start watch mode (tests re-run on file changes)
make test_watch

# Terminal 2: Edit code and format
# Changes automatically trigger test re-runs in Terminal 1
make format

# When satisfied, commit
git add .
git commit
```

This workflow provides:
- Immediate feedback on failing tests
- Auto-formatting and linting
- No need to manually re-run commands

### Linting Changed Files Only

When working on a large file or branch, lint only what changed:

```bash
# Format only files changed vs. master
make format_diff

# Lint only changed files
make lint_diff

# Reduces noise and speeds up feedback
```

These targets use `git diff --relative=libs/<package> --name-only` to identify changed files.

### Type Checking Specific Code

When developing or debugging type errors:

```bash
# Type check a single file
mypy libs/langchain_v1/langchain/agents/agent.py

# Type check a directory
mypy libs/langchain_v1/langchain/agents/

# Type check tests (uses separate cache to avoid build overhead)
cd libs/langchain_v1
make lint_tests

# Type check just the package, not tests
make lint_package
```

### Adding a New Dependency

When you need to add or update a dependency:

```bash
# 1. Navigate to package directory
cd libs/langchain_v1

# 2. Edit pyproject.toml to add/update the dependency in the correct section
#    (dependencies, test, lint, typing, dev, or test_integration)

# 3. Regenerate the lock file
uv lock

# 4. Test the new dependency works
make test

# 5. Commit both pyproject.toml and uv.lock
git add pyproject.toml uv.lock
git commit -m "chore(langchain_v1): add new_library dependency"
```

### Simulating CI Locally

To run the exact same checks that CI will run:

```bash
# 1. Navigate to the package
cd libs/langchain_v1

# 2. Sync all dependencies
uv sync --all-groups

# 3. Run pre-commit on all files (simulates pre-commit hook behavior)
pre-commit run --all-files

# 4. Run full test suite
make test

# 5. Run full linting and type checking
make lint
```

If all steps pass, your PR is ready for review. CI will run the same checks on your branch.

## Environment Variables and Configuration

The Makefiles and development commands use several environment variables to control behavior:

| Variable | Purpose | Default | Usage |
|----------|---------|---------|-------|
| `UV_FROZEN` | Prevent lock file changes during `uv sync` | `true` (in Makefiles) | Prevents accidental lock modifications during regular `uv sync` |
| `TEST_FILE` | Path to test file or directory to run | `tests/unit_tests/` | Override: `make test TEST_FILE=tests/unit_tests/agents/` |
| `PYTEST_EXTRA` | Extra pytest command-line options | (empty) | Override: `make test PYTEST_EXTRA="-vv -s --pdb"` |
| `LANGGRAPH_TEST_FAST` | Use in-memory services (fast) vs. Docker (full) | `0` (Docker) or `1` (fast) | Set in `langchain_v1`: `LANGGRAPH_TEST_FAST=1 make test` |
| `PYTHON_FILES` | Files to lint/format (set by targets) | `.` (all) | Internal variable set by `make lint_diff`, `make format_diff` |
| `MYPY_CACHE` | Directory for mypy type-checking cache | `.mypy_cache` | Separate cache for tests: `.mypy_cache_test` |

### Example Commands with Environment Variables

```bash
# Run tests in verbose mode with print statement output
make test PYTEST_EXTRA="-vv -s"

# Run tests with debugger on failure
make test PYTEST_EXTRA="--pdb"

# Run fast tests without Docker services (langchain_v1)
LANGGRAPH_TEST_FAST=1 make test

# Run only a subset of tests with verbosity
make test TEST_FILE=tests/unit_tests/agents PYTEST_EXTRA="-vv -k test_agent"

# Format only changed files and lint them
make format_diff
make lint_diff
```

### Dependency Group Selection

Use `uv sync` with `--group` to control which tool groups are installed:

```bash
# Install only test tools (pytest, pytest-cov, etc.)
uv sync --group test

# Install only linting tools (ruff, mypy)
uv sync --group lint

# Install typing tools (mypy and stubs)
uv sync --group typing

# Install development tools (jupyter, etc.)
uv sync --group dev

# Install everything (all groups)
uv sync --all-groups
```

Each `pyproject.toml` defines dependency groups under `[dependency-groups]`:

## Troubleshooting

### Lock File Out of Sync

**Error**: `uv sync` fails or complains about dependency conflicts

```bash
# Check if lock file is out of date
uv lock --check

# Regenerate lock (if pyproject.toml changed)
uv lock

# Or regenerate all package locks
cd libs
make lock
```

**Prevention**: The `UV_FROZEN=true` setting in Makefiles prevents accidental lock changes during `uv sync`.

### Dependencies Not Installed

**Error**: `pytest: command not found` or `ruff: command not found`

```bash
# Ensure test group is installed
uv sync --group test

# Ensure lint and typing groups are installed
uv sync --group lint --group typing

# Install everything (recommended for development)
uv sync --all-groups

# Verify installation
uv run pytest --version
uv run ruff --version
```

### Tests Fail with "Socket Error" or "No Network"

**Error**: Tests error out with `socket.gaierror` or "connection refused"

This is intentional—unit tests have socket restrictions to prevent accidental network calls. Two solutions:

```bash
# 1. Run integration tests instead (if testing network-dependent code)
make integration_tests

# 2. Or add API keys/environment and run specific integration test file
export OPENAI_API_KEY="..."
make integration_tests TEST_FILE=tests/integration_tests/llms/test_openai.py
```

Unit tests use `pytest-socket` to enforce `--disable-socket` by default.

### "Ruff" or "Mypy" Not Found

**Error**: `ruff: command not found` when running `make lint` or `ruff check .`

```bash
# Install all tool groups
uv sync --all-groups

# Or install just the tools you need
uv sync --group lint --group typing

# Verify installation
which ruff
which mypy

# If still not found, use uv run to invoke them
uv run ruff check .
uv run mypy .
```

### Pre-Commit Hook Fails Locally But Passes in CI

**Error**: Hook fails with format/lint/type errors when you run `pre-commit run --all-files`

```bash
# 1. Ensure you're in the right directory
cd libs/langchain_v1  # Where changes were made

# 2. Check Python version matches CI (usually in .github/workflows)
python --version

# 3. Install all dependency groups
uv sync --all-groups

# 4. Manually run the failing make target
make format
make lint

# 5. Commit and try the hook again
git add .
pre-commit run --all-files
```

**Common causes**:
- Different Python versions between local and CI
- Missing dependency groups (run `uv sync --all-groups`)
- Stale pre-commit cache: `pre-commit clean` and retry

### "No Module Named Pytest"

**Error**: `ModuleNotFoundError: No module named 'pytest'`

```bash
# The test group isn't installed
uv sync --group test

# Or if running pytest via make, check your current directory
cd libs/langchain_v1  # (example)
make test

# Verify pytest is available
uv run pytest --version
```

### Tests are Slow

**Issue**: Test suite takes a long time to run

```bash
# Run only a specific test file instead of all tests
make test TEST_FILE=tests/unit_tests/agents/test_agent.py

# Run in watch mode and only re-run changed tests
make test_watch

# For langchain_v1, use fast mode (in-memory services)
make test_fast

# Run only tests that failed last time
make test PYTEST_EXTRA="--lf"

# Parallelize more aggressively
make test PYTEST_EXTRA="-n 16"  # Run 16 tests in parallel
```

### "python: No such file or directory"

**Error**: Commands fail with `python: command not found`

```bash
# uv manages Python—don't call python directly
# Use uv run instead
uv run python --version

# Or let uv sync handle it
uv sync --all-groups

# Most make targets use uv run internally, so just use make
make test
make lint
```

### Type Checking is Very Slow

**Issue**: `make type` or `make lint` takes minutes to complete

```bash
# Clear mypy cache (can become stale)
rm -rf .mypy_cache .mypy_cache_test

# Type check a specific file instead of the whole package
mypy libs/core/langchain_core/agent.py

# Type check tests only (usually faster)
make lint_tests

# Type check just the package source (not tests)
make lint_package
```

## Related Documentation

- [Contributing Guide (AGENTS.md)](repo://AGENTS.md): Detailed development conventions, PR templates, code quality standards, and testing requirements
- [Unit Tests](repo:///openwiki/unit-tests.md): Test organization, fixtures, mocking patterns, and pytest best practices
- [Integration Tests](repo:///openwiki/integration-tests.md): Setting up integration tests, managing external dependencies and API keys
- [CI Workflows](repo:///openwiki/ci-workflows.md): GitHub Actions automation, version checks, release process, and CI/CD pipeline
- [Quickstart Guide](repo:///openwiki/quickstart.md): Getting started with the LangChain monorepo
