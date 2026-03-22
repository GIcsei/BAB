# Contributing to BAB

Thank you for considering a contribution to the Bank Analysis Backend! This guide covers contribution rules, testing expectations, and the documentation workflow.

## Getting Started

1. Fork the repository and clone your fork.
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature main
   ```
3. Install dev dependencies:
   ```bash
   pip install uv
   uv sync --frozen --group dev
   ```

## Code Standards

- **Python 3.12** — all code must be compatible.
- **Type annotations** — required for all new code (`mypy --strict`).
- **Formatting** — enforced by Black (line length 88) and isort (profile `black`).
- **Linting** — enforced by Ruff (`E`, `F`, `W`, `I`, `B` rules).
- Run quality checks locally before pushing:
  ```bash
  uv run ruff check app tests
  uv run black --check app tests
  uv run mypy app
  ```

## Testing

- All new code must include tests.
- Tests live under `tests/` in `unittest/`, `integrationtest/`, and `functionaltest/` directories.
- Run the full suite with coverage:
  ```bash
  uv run pytest -v --cov=app --cov-fail-under=70
  ```
- CI enforces a minimum 70 % coverage threshold.
- See [Testing Instructions](docs/testing.md) for details on test structure and writing new tests.

## Pull Request Process

1. Ensure all checks pass locally (lint, typecheck, tests, security scan).
2. Open a pull request against `main`.
3. CI will run lint, type checking, tests with coverage, and security scans automatically.
4. Address any review feedback and keep the branch up to date with `main`.

## Documentation Workflow

Documentation lives in the `docs/` directory and is built with [MkDocs](https://www.mkdocs.org/) using the [Material](https://squidfundamental.github.io/mkdocs-material/) theme.

### Editing Documentation

- All Markdown files are in `docs/`. Navigation is configured in `mkdocs.yml`.
- When adding a new page, update the `nav` section in `mkdocs.yml` and add a link in `docs/index.md`.

### Local Preview

Build and serve the documentation site locally:

```bash
pip install mkdocs-material
mkdocs serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) to preview changes.

### Deployment

Documentation is deployed automatically to [GitHub Pages](https://gicsei.github.io/BAB/) via the `.github/workflows/pages.yml` workflow:

- **Trigger**: every push to `main` and every release tag (`v*`).
- **Process**: MkDocs builds the `docs/` directory into static HTML in `site/`, which is uploaded and deployed to GitHub Pages.
- **Badge**: the deployment status badge is shown in `README.md`.

No manual deployment steps are required. Simply merge your changes to `main` and the site updates automatically.

### MkDocs Configuration

The `mkdocs.yml` at the repository root controls:

- Site metadata (name, URL, repository link).
- Theme settings (Material with light/dark toggle).
- Navigation structure.
- Markdown extensions (admonitions, code highlighting, tables, etc.).

## Security

- Never commit credentials, secrets, or service-account keys.
- Run `uv run pip-audit` and `uv run bandit -r app -ll` before submitting.
- Report vulnerabilities privately via [GitHub Security Advisories](https://github.com/GIcsei/BAB/security/advisories/new).

## Code of Conduct

Be respectful and constructive. We follow standard open-source community norms.
