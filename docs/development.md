# Development guide

For contributors and anyone building from source.

## Setup

```bash
git clone https://github.com/seanebones-lang/personal-RAG.git
cd personal-RAG
./scripts/setup.sh
source .venv/bin/activate
pip install -e ".[dev]"
```

## Project structure

```
personal-RAG/
├── src/
│   ├── cli.py              # Typer entry
│   ├── config.py           # Settings
│   ├── ollama_client.py
│   ├── ingest/
│   ├── embed/
│   └── store/
├── tests/
├── docs/
├── .github/workflows/ci.yml
├── pyproject.toml
└── requirements.txt
```

## Running tests

```bash
# Fast unit tests (no model download)
pytest -m "not integration" -v

# All tests
pytest -v
```

Tests use a temporary `PRV_DB_PATH` per test (see `tests/conftest.py`).

## Lint and types

```bash
ruff check src tests
ruff format src tests
mypy src
```

Or:

```bash
make lint
make format
make test
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) on push/PR to `main` / `master`:

- Python 3.10 and 3.12
- `ruff check` + `ruff format --check`
- `mypy src`
- `pytest -m "not integration"`

## Adding a feature

1. Open an issue or comment on an existing one.
2. Branch from `main`: `git checkout -b feat/my-feature`
3. Add tests in `tests/`.
4. Run `make test` and `make lint` locally.
5. Update docs in `docs/` if behavior is user-visible.
6. Open a PR using the template.

See [CONTRIBUTING.md](../CONTRIBUTING.md).

## Integration tests

Mark slow tests that need the real embedding model or Ollama:

```python
import pytest

@pytest.mark.integration
def test_real_embed():
    ...
```

Run with: `pytest -m integration`

## Release checklist (maintainers)

1. Update version in `pyproject.toml` and `src/__init__.py`
2. Add entry to [CHANGELOG.md](../CHANGELOG.md)
3. Tag: `git tag v0.1.1`
4. Push tag and `main`
