# Contributing to PersonalRAGVault

Thank you for helping make PersonalRAGVault better. This project is open source under the [MIT License](LICENSE).

## Ways to contribute

- Report bugs or request features via [GitHub Issues](https://github.com/seanebones-lang/probable-fishstick/issues)
- Improve documentation in `docs/` or `README.md`
- Fix bugs or add features with pull requests
- Share usage feedback and examples

## Before you start

1. Read [docs/getting-started.md](docs/getting-started.md) and [docs/development.md](docs/development.md)
2. Search existing issues to avoid duplicates
3. For large changes, open an issue first to discuss approach

## Development setup

```bash
git clone https://github.com/seanebones-lang/probable-fishstick.git
cd probable-fishstick
./scripts/setup.sh
source .venv/bin/activate
pip install -e ".[dev]"
pytest -m "not integration" -v
```

## Pull request guidelines

- Branch from `main` with a descriptive name (`fix/chroma-empty-query`, `docs/cli-examples`)
- Keep PRs focused; one logical change per PR when possible
- Add or update tests for behavior changes
- Run locally before pushing:

  ```bash
  ruff check src tests && ruff format src tests
  mypy src
  pytest -m "not integration" -v
  ```

- Update user-facing docs if CLI, config, or install steps change
- Write a clear PR description: what, why, how to test

## Code style

- Python 3.10+ compatible
- Follow existing patterns in `src/`
- Use `logging` in library code; Rich output in `cli.py`
- Prefer small, readable functions over heavy abstraction

## Commit messages

Use clear, imperative subjects:

- `fix: clamp Chroma n_results when collection is small`
- `docs: add architecture diagram`
- `feat: support .rst ingestion`

## Community

Be respectful and constructive. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Questions

Open a [GitHub Discussion](https://github.com/seanebones-lang/probable-fishstick/discussions) or an issue labeled `question` if discussions are enabled; otherwise use Issues.
