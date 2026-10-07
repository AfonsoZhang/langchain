---
type: "Reference"
title: "CI/CD Workflows: GitHub Actions and Release Process"
description: "LangChain's GitHub Actions-based CI/CD system automating testing, linting, and release management across a monorepo with intelligent change detection, parallel matrix testing, and strict release gates."
tags: [ci-cd, github-actions, testing, linting, release, pypi, monorepo, automation]
verified:
  - by: openwiki/0.5.0
    at: 2026-10-07T08:30:45.453Z
sources:
  - id: openwiki-source-34e57b5a3a0c875639ab72a7
    resource: repo://.github/scripts/check_diff.py
  - id: openwiki-source-f35e7c44cc1805709393a581
    resource: repo://.github/workflows/_lint.yml
  - id: openwiki-source-c92cc62695c6def991956428
    resource: repo://.github/workflows/_release.yml
  - id: openwiki-source-c9c292f4ecabe180cdae27ce
    resource: repo://.github/workflows/_test_pydantic.yml
  - id: openwiki-source-d8a8900818f4abab719bd1b7
    resource: repo://.github/workflows/_test_vcr.yml
  - id: openwiki-source-4d9cccca7700db7220ec055e
    resource: repo://.github/workflows/_test.yml
  - id: openwiki-source-7330cb37457ccdb62d7c41c7
    resource: repo://.github/workflows/auto-label-by-package.yml
  - id: openwiki-source-6e3a52c89729b5704dbd7eec
    resource: repo://.github/workflows/check_diffs.yml
  - id: openwiki-source-9069a5dd5fbb579fbd5470ce
    resource: repo://.github/workflows/integration_tests.yml
  - id: openwiki-source-6d4b4e707b8d60b6ccfa3425
    resource: repo://.github/workflows/openwiki-update.yml
  - id: openwiki-source-f8781d847f6481a966a44a68
    resource: repo://.github/workflows/pr_labeler.yml
  - id: openwiki-source-12805fbf767dc2a3e238645e
    resource: repo://.github/workflows/pr_lint.yml
generated: { by: "openwiki/0.5.0", at: "2026-10-07T08:30:45.453Z" }
---

# CI/CD Workflows: GitHub Actions and Release Process

LangChain employs a sophisticated CI/CD system built on GitHub Actions that automates testing, linting, quality checks, and release management across a monorepo structure. The system emphasizes efficiency through intelligent change detection, parallel matrix testing, and strict release gates.

## Architecture Overview

The CI/CD system consists of three layers:

1. **Pull request / push CI (`check_diffs.yml`)**: Detects changed packages and runs targeted tests, linting, and compatibility checks
2. **Scheduled integration testing (`integration_tests.yml`)**: Daily remote API testing with live credentials against partner libraries
3. **Manual release workflow (`_release.yml`)**: Comprehensive pre-release validation, PyPI publishing, and dependent package testing

## Primary CI Workflow (Pull Requests & Master Pushes)

The main entry point is `.github/workflows/check_diffs.yml`, which runs on every pull request, push to master, and merge group event.

### Change Detection & Matrix Generation

The workflow begins with a change detection phase:

1. A Python script (`.github/scripts/check_diff.py`) analyzes which files changed
2. Maps changes to package directories (`libs/core`, `libs/partners/*`, etc.)
3. Builds a dependency graph to include dependent packages when core components change
4. Generates separate test matrices for linting, unit tests, Pydantic compatibility tests, integration test compilation, VCR cassette tests, and extended test suites
5. Outputs are passed as JSON to downstream jobs via matrix strategy

This detection ensures only affected packages are tested, optimizing CI runtime. The script skips the `libs/standard-tests` directory in enumeration and treats certain partners (e.g., huggingface) as CI-unstable, removing them from dependent chains while allowing direct edits to be tested.

### Linting Pipeline (`_lint.yml`)

Runs on affected packages with Python 3.11 (configurable):

- **Ruff analysis**: Code style, import sorting, and rule enforcement with inline GitHub annotations (via `RUFF_OUTPUT_FORMAT: github`)
- **MyPy type checking**: Static type verification
- **Markdown linting**: Documentation quality checks (via `.markdownlint.json`)

Tools are sourced from dependency groups: `lint` and `typing`. The workflow installs both package code and test code dependencies, running `make lint_package` and `make lint_tests` targets. Partner packages receive separate test dependency installation including integration test dependencies.

### Unit Testing (`_test.yml`)

Runs matrix tests across Python versions with dependency constraint verification:

**Matrix dimensions**:
- Python 3.10, 3.11, 3.12, 3.13, 3.14 for `libs/core`
- Python 3.10 and 3.14 for other packages
- Current locked dependencies (from `uv.lock`)
- Minimum supported dependency versions

**Two-phase testing**:

1. **Current dependencies**: Runs full test suite against versions in `uv.lock` via `make test PYTEST_EXTRA=-q`
2. **Minimum dependencies**: Calculates minimum versions from `pyproject.toml` constraints via `get_min_versions.py` script, downgrades via pip, and reruns tests with `make tests PYTEST_EXTRA=-q` to ensure compatibility

The workflow verifies the working directory remains clean (no untracked generated files) after testing. This two-phase approach catches issues where code relies on buggy behavior in older dependencies or where minimum version specifications are too permissive.

### Pydantic Compatibility Testing (`_test_pydantic.yml`)

Tests affected packages against configurable Pydantic versions (e.g., v2.0, v2.1, v2.2):

- Triggered when Pydantic version constraints or dependent code changes
- Determines test matrix by querying `uv.lock` for max Pydantic version and `pyproject.toml` for min, across both core and target packages
- Runs `make test` against each Pydantic version
- Uses Python 3.12 by default with override support

### VCR Cassette Tests (`_test_vcr.yml`)

Validates integration tests backed by recorded HTTP cassettes:

- Runs in playback-only mode with fake credentials (no real API keys required)
- Detects stale cassettes from test input changes without re-recording
- Executes `make test_vcr` target
- Enables fast, repeatable integration test feedback

Only triggered for packages with VCR cassettes (currently `libs/partners/openai`), as tracked in the `VCR_PACKAGES` set within `check_diff.py`.

### Integration Test Compilation (`_compile_integration_test.yml`)

Performs shallow integration test validation:

- Compiles test modules without executing them via `pytest -m compile tests/integration_tests`
- Catches import errors and obvious syntax issues
- Provides quick feedback loop without running expensive external API calls
- Installs both test and integration test dependency groups

### Extended Test Suites

For packages defining `extended_testing_deps.txt`, runs additional tests:

- Installs extra dependencies beyond standard test group via the file
- Executes `make extended_tests` target
- Allows performance benchmarks, stress tests, or heavy-weight validations
- Located in the `extended-tests` job within `check_diffs.yml`

### Release Option Validation

The workflow includes a `check-release-options` job:

- Verifies `.github/workflows/_release.yml` dropdown options stay synchronized with actual package directories
- Prevents stale release options from blocking valid releases

## Integration Testing Workflow (`integration_tests.yml`)

The scheduled integration testing workflow runs live integration tests against real APIs with valid credentials. This supplements VCR cassette testing by validating actual behavior against live services.

### Scheduling and Manual Triggers

- **Scheduled**: Runs daily at 1 PM UTC (9 AM EDT / 6 AM PDT) via cron schedule
- **Manual dispatch**: Can be triggered on-demand via GitHub Actions UI
- **Fork safety**: Scheduled runs only execute on the main repository; forks can still manually trigger runs

### Matrix Generation

The workflow starts with a `compute-matrix` job that generates test parameters:

**Default configuration** (9 partner libraries):
- `libs/partners/openai`
- `libs/partners/anthropic`
- `libs/partners/fireworks`
- `libs/partners/groq`
- `libs/partners/mistralai`
- `libs/partners/xai`
- `libs/partners/google-vertexai`
- `libs/partners/google-genai`
- `libs/partners/aws`

**Python versions**: 3.10 and 3.14 (default); override via input

**Dispatch options**:
- Select individual libraries from dropdown
- Exclude specific libraries from all-run (e.g., `exclude: openai,anthropic`)
- Override working-directory to arbitrary path
- Override Python versions

### Test Execution and Library Selection

The `integration-tests` job executes for each matrix combination:

1. **Checkout main repo**: Clone the main langchain repository
2. **Checkout external repos**: Fetch google-genai, google-vertexai, and aws packages from separate repositories
3. **Reorganize external packages**: Move external library files into `libs/partners/` directory structure to integrate with main monorepo
4. **Install dependencies**: Run `uv sync --group test --group test_integration` within each package
5. **Overlay local core**: For external packages without `[tool.uv.sources]` declarations, explicitly install local editable versions of core and standard-tests
6. **Execute tests**: Run `make integration_tests` within the package directory

### Concurrency and Credential Management

- **Concurrency locks**: Grouped per `(working-directory, python-version)` to serialize same-package tests across different workflow runs
- **Within-run parallelism**: Different Python versions run in parallel within a single workflow execution
- **Credential scope**: Tests run in `Scheduled testing` environment, scoped to receive 30+ API credential secrets:
  - Model API keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, FIREWORKS_API_KEY, etc.
  - Search/data APIs: GOOGLE_API_KEY, EXA_API_KEY, MONGODB_ATLAS_URI
  - Cloud credentials: AWS keys, Azure OpenAI credentials, Google Cloud credentials
  - LangSmith tracing: LANGSMITH_API_KEY, LANGSMITH_GATEWAY credentials
  - Special resources: ANTHROPIC_FILES_API_IMAGE_ID, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME

### LangSmith Integration

Integration tests report results to LangSmith tracing:
- LANGSMITH_PROJECT: `scheduled-testing-py` by default
- Tags include package name, Python version, and commit SHA
- Metadata includes GitHub run ID and URL for correlation
- Enables failure investigation via trace history

### Dependent Package Testing

The `test-dependents` job validates external packages depending on LangChain:

- Currently tests `deepagents` (requires Python 3.11+)
- Checks out external repo and local LangChain core
- Installs external package with test dependencies
- Overlays local langchain-core and langchain_v1 editable installs
- Runs `make test` to catch breaking changes before release

## Dependency Management: uv.lock and Version Pinning

All CI jobs set `UV_FROZEN=true` to ensure reproducible builds:

- Locks all transitive dependencies to versions specified in `uv.lock`
- Prevents silent upgrades of transitive dependencies
- Ensures CI environment matches local developer environments

**Two-phase dependency testing**:
1. **Current dependencies**: Validates against locked versions in `uv.lock`
2. **Minimum dependencies**: Downgrades to minimum supported versions from `pyproject.toml` constraints and retests

This approach catches issues where:
- Code accidentally relies on newer behavior in transitive dependencies
- Minimum version specifications are too loose (e.g., `>=2.0.0` when code requires `2.5.0`)
- Package constraints conflict with actual usage

The `get_min_versions.py` script calculates minimum versions by:
1. Reading `pyproject.toml` version constraints (e.g., `pydantic>=2.0.0`)
2. Querying PyPI for actual minimum released versions satisfying those constraints
3. Supporting two modes: `pull_request` (lenient, warns on prereleases) and `release` (strict, fails on any prerelease)

## Release Workflow (`_release.yml`)

The release workflow is manually triggered via GitHub Actions UI (or can be called as a reusable workflow). It handles versioning, building, testing, and publishing to PyPI.

### Release Modes & Invocation

**Manual dispatch** (`workflow_dispatch`):
- Dropdown selection of package to release (core, langchain, langchain_v1, text-splitters, standard-tests, model-profiles, or 17+ partner packages)
- Manual version entry (default `0.1.0`)
- Optional override to full path (e.g., `libs/partners/partner-xyz`)
- Dangerous flags: `dangerous-nonmaster-release` (hotfixes), `allow-prereleases`, `skip-prior-published-package-checks`

**Reusable workflow** (`workflow_call`):
- Accepts `working-directory`, `release-version`, and safety bypass flags
- Used internally for multi-package release orchestration

### Release Gate: Build & Version Check

**Job: `build`** (isolated permissions for security):

1. **Version verification**: Extracts version from `pyproject.toml` and compares against input using PEP 440 normalization (treating `0.1.0-rc1` and `0.1.0rc1` as equivalent); fails if mismatch
2. **PyPI availability check**: Queries `https://pypi.org/pypi/{pkg}/{version}/json` to ensure version not already published; fails closed if PyPI is unreachable or returns unexpected status
3. **Build**: Runs `uv build` to create wheel and sdist distributions
4. **Artifact upload**: Stores `dist/` directory for downstream jobs

Security rationale: Separates build (no credentials) from publishing (trusted publishing token) to prevent compromised dependencies from accessing PyPI credentials.

### Release Notes Generation

**Job: `release-notes`**:

1. **Tag detection**: Finds previous release tag via git history
   - For pre-releases (contains hyphen): Matches base version; falls back to latest release tag
   - For stable releases: Searches for previous patch version; falls back to latest
   - First release: Uses full commit history from git root
2. **Changelog extraction**: Runs `git log --format="%s" <prev-tag>..HEAD -- <working-dir>` to collect commit messages
3. **Tag validation**: Confirms previous tag exists in git repo before proceeding

### Pre-Release Checks

**Job: `pre-release-checks`** (no caching to catch missing dependencies):

1. **Direct wheel installation**: Installs built wheel directly via `uv pip install dist/*.whl` (validates metadata and installability)
2. **Package import test**: Verifies main module imports successfully
3. **Unit tests**: Runs full `make tests` against the wheel
4. **Minimum version testing**: Recalculates minimum versions, downgrades via pip, and reruns tests with `make tests PYTEST_EXTRA="-q -k 'not test_serdes'"` (skips serialization tests for speed)
5. **Prerelease dependency detection**: Fails if any dependencies declare prerelease versions (unless release itself is prerelease)
6. **Integration tests**: For partner packages only, runs `make integration_tests` with live API credentials

### PyPI Publishing

**Job: `test-pypi-publish`** (TestPyPI):
- Uses GitHub OpenID Connect (trusted publishing)
- Publishes to test.pypi.org for staging validation
- Tolerates duplicate versions via `skip-existing: true` (CI safety only)

**Job: `publish`** (Production PyPI):
- Uses trusted publishing to production PyPI
- Only runs if all prior checks pass
- Creates GitHub Release with generated release notes

### Compatibility Testing

**Job: `test-prior-published-packages-against-new-core`**:
- Only runs for `libs/core` releases
- Tests previously-published partner packages (currently anthropic, openai) against new core
- Fetches latest non-yanked published partner tag from git, installs new core wheel, runs tests

## Troubleshooting CI Issues

### Debugging Matrix Generation

If tests aren't running for expected packages:

1. Check `.github/scripts/check_diff.py` for package directory configuration
2. Verify changed files match package directories (e.g., changes under `libs/partners/openai/` affect `libs/partners/openai`)
3. Run check_diff.py locally with a subset of files to test matrix logic
4. Check `check-release-options` job for dropdown synchronization issues

### Local Simulation of CI Workflows

Reproduce unit tests locally:

```bash
# Install dependencies
cd libs/core
uv sync --all-groups

# Run unit tests (same as CI)
make test PYTEST_EXTRA=-q

# Simulate minimum version testing
VIRTUAL_ENV=.venv uv pip install packaging tomli requests
python_version="$(python --version | awk '{print $2}')"
min_versions="$(./.venv/bin/python ../.github/scripts/get_min_versions.py pyproject.toml pull_request $python_version)"
VIRTUAL_ENV=.venv uv pip install $min_versions
make tests PYTEST_EXTRA=-q
```

Reproduce linting locally:

```bash
# Install lint and typing tools
uv sync --group lint --group typing

# Run linting
make lint_package
make lint_tests
```

### Handling Matrix Configuration Issues

**Problem**: Test matrix includes unexpected packages
- Check if changes to core or shared packages affect dependent calculations
- Review `IGNORE_CORE_DEPENDENTS` flag in check_diff.py
- Verify `IGNORED_PARTNERS` list for exclusions

**Problem**: Pydantic compatibility tests fail
- Check `_get_pydantic_test_configs()` in check_diff.py for version range calculation
- Ensure `pyproject.toml` constraints include expected Pydantic range
- Verify `uv.lock` contains packages for min/max versions

**Problem**: Integration tests timeout or fail sporadically
- Check credential secret configuration in `Scheduled testing` environment
- Verify external repository checkouts (google-genai, google-vertexai, langchain-aws) have access
- Review concurrency locks to prevent parallel access to shared credentials
- Check LangSmith project limits (scheduled-testing-py)

### Common CI Failures

**"working tree not clean"**: 
- Test generated files without committing them
- Check `git status` in test output
- Verify `make test` target doesn't create artifacts

**Minimum version test fails**:
- Check if test requires features from newer dependency versions
- Review `get_min_versions.py` output for unexpected minimum versions
- Verify `pyproject.toml` constraints match actual dependency usage

**Release workflow blocked**:
- Verify version in `pyproject.toml` matches input version
- Check PyPI to ensure version not already published
- Review prerelease dependencies via `pip freeze` on built wheel
- Confirm release branch is master or enable `dangerous-nonmaster-release`

### Monitoring Scheduled Integration Tests

Integration tests run daily and should be monitored:

1. Check GitHub Actions tab for "⏰ Integration Tests" workflow
2. Review failed steps in test-dependents or integration-tests jobs
3. Check LangSmith project `scheduled-testing-py` for trace data
4. For credential issues, verify `Scheduled testing` environment secrets haven't expired
5. For external repo issues, verify google-genai and langchain-aws repositories are accessible
