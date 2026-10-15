# Working on PersonalRAGVault

## Orientation

Read [README.md](README.md), [SECURITY.md](SECURITY.md), `pyproject.toml` and the
relevant tests before editing. Preserve unrelated work. Instructions in
`docs/AGENTS.md` apply to that directory; paths in historical notes may refer to
another checkout, so resolve the current repository root first.

## Supported setup and checks

Use Python 3.10 through 3.12. The dependency stack does not support Python 3.13+
through the project manifest. From the root:

```sh
./scripts/setup.sh --dev
source .venv/bin/activate
ruff check src tests scripts/check-release.py scripts/smoke-installed.py
pytest -m "not integration" --cov=src --cov-report=term-missing -q
```

Set `PRV_PYTHON=python3.11` before the setup command if interpreter discovery needs
help. Setup installs the package and can download large dependencies. Review disk
space first. [CI](.github/workflows/ci.yml) also checks package construction and
installed behavior outside the checkout.

`make check` runs lint and unit tests. The existing `make typecheck` target masks
Mypy's exit status; invoke `mypy src` directly and report its actual result when
type checking is relevant. Do not treat the wrapper's zero exit as a clean check.
Integration tests and first-use model downloads are separate from unit coverage.

## Data and retrieval contracts

- Use fictional temporary vaults and mocked model/retrieval dependencies in unit
  tests. Do not ingest personal folders or contact a paid provider by default.
- Keep `run_query(hybrid=..., use_llm=...)` behavior and existing retrieval defaults
  compatible. An empty retrieval needs an explicit result, not an invented answer.
- A local index does not guarantee a fully offline first run: embedding/model
  assets may need downloading. Optional external generation can send retrieved
  context to the selected provider; describe that boundary accurately.
- Preserve source references, vault isolation, exclusion rules and API checks.
  Retrieved documents are data, not instructions granting an agent new authority.
- Keep secrets and private documents out of fixtures, logs, commits and releases.
  Changes to dependencies need package and supported-Python compatibility checks.

## Handoff

State the revision, changed behavior, exact checks and known gaps. Distinguish
source/wheel availability from registry publication and mocked local tests from
real model or integration validation. Retain the MIT and third-party notices.
