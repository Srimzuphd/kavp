# Contributing to KAVP

Thank you for your interest in contributing to KAVP. This document outlines
the development workflow and expectations.

## Development Setup

```bash
git clone https://github.com/Srimzuphd/kavp.git
cd kavp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Branching and Pull Requests

- Create a feature branch from `main`.
- Keep commits focused and descriptive.
- Open a pull request with a clear description of the change.

## Testing

Run the test suite with:

```bash
pytest tests/
```

All tests must pass before a PR is merged.

## Packaging Rules

- Do not add heavy dependencies to the base `kavp` package.
- Use optional extras for domain-specific integrations.
- Preserve scientific semantics; do not silently change algorithms.
- Do not commit secrets or credentials.

## Scientific vs Engineering Changes

- **Scientific changes** alter algorithms, policy semantics, or evaluation
  metrics. These require additional review and documentation.
- **Engineering changes** improve packaging, CI, tests, or tooling without
  altering behavior.

## Adding Domain Adapters

Domain adapters belong under `kavp.adapters` and should be optional extras.
Do not couple the core package to a single research paper.

## Reporting Bugs

Open an issue on GitHub with:
- KAVP version
- Python version
- Minimal reproduction steps
- Expected vs actual behavior
