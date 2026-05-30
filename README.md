# PersonalRAGVault

[![CI](https://github.com/seanebones-lang/personal-RAG/actions/workflows/ci.yml/badge.svg)](https://github.com/seanebones-lang/personal-RAG/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Local-first RAG for your personal files.** Ingest PDFs, notes, code, and exports from a folder on your machine, embed them with a lightweight CPU model, store vectors in ChromaDB, and query with natural language—optionally answered by a local [Ollama](https://ollama.com/) model.

No cloud. No account. Your data stays on your disk.

## Why PersonalRAGVault?

- **Private** — runs entirely on your Mac or Linux machine
- **Simple** — one CLI, no Docker or database server to operate
- **Practical** — chunking, dedup on re-ingest, folder watch, retrieval-only mode
- **Hackable** — small Python codebase, documented for contributors

## Features

| Feature | Description |
|---------|-------------|
| Ingest | PDF, TXT, MD, JSON, DOCX, and common code/text formats |
| Chunking | Overlapping chunks for better retrieval on large documents |
| Dedup | Stable chunk IDs; re-ingest updates instead of duplicating |
| Query | Vector search + optional Ollama generation (`--no-llm` for retrieval only) |
| Watch | Debounced folder watching for automatic re-ingest |
| Manage | `status`, `purge`, `reindex` commands |

## Quick start

**Run all commands from the project directory** (where `pyproject.toml` lives).

```bash
git clone https://github.com/seanebones-lang/personal-RAG.git
cd personal-RAG

./scripts/setup.sh --dev    # or: python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

ollama pull llama3.2        # optional; skip if using --no-llm

personalragvault ingest ~/Downloads
personalragvault query "find my notes about RAG systems"
```

See **[docs/getting-started.md](docs/getting-started.md)** for the full walkthrough.

## New in v0.2

- `personalragvault models list` — embedding presets (mini, bge-small, bge-base)
- `--hybrid` query — BM25 + vector fusion
- `--where-year`, `--source-contains`, `--extension` — metadata filters
- `.eml` / `.mbox` ingest — email archives
- `personalragvault compact` — maintain sidecar indexes
- `personalragvault ui` — optional local Streamlit UI (`pip install -e ".[ui]"`)

## Documentation

| Guide | Description |
|-------|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [Getting started](docs/getting-started.md) | Install, ingest, query |
| [CLI reference](docs/cli-reference.md) | Commands and flags |
| [Configuration](docs/configuration.md) | Environment variables |
| [Architecture](docs/architecture.md) | How the pipeline works |
| [FAQ](docs/faq.md) | Troubleshooting |
| [Development](docs/development.md) | Tests, lint, CI |
| [Contributing](CONTRIBUTING.md) | Issues and pull requests |

## Requirements

- Python 3.10+ (3.10–3.12 tested in CI)
- ~500MB+ disk for dependencies; embedding model downloads on first ingest
- [Ollama](https://ollama.com/) optional (use `--no-llm` without it)

## Commands (summary)

```bash
personalragvault ingest PATH [--recursive] [--verbose]
personalragvault query "QUESTION" [--no-llm] [--top-k N]
personalragvault watch PATH
personalragvault status
personalragvault purge [--yes]
personalragvault reindex PATH [--yes]
```

Alternative entry point: `python -m src.cli <command>`

## Configuration

Copy [`.env.example`](.env.example) to `.env` or export variables. Key settings:

| Variable | Default |
|----------|---------|
| `PRV_DB_PATH` | `~/.personalragvault/chroma` |
| `PRV_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` (~22M params) |
| `OLLAMA_MODEL` | `llama3.2` |

Full list: [docs/configuration.md](docs/configuration.md)

## Development

```bash
make setup-dev    # venv + editable install with dev tools
make check        # ruff + mypy + pytest
```

Details: [docs/development.md](docs/development.md)

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

- [Report a bug](https://github.com/seanebones-lang/personal-RAG/issues/new?template=bug_report.yml)
- [Request a feature](https://github.com/seanebones-lang/personal-RAG/issues/new?template=feature_request.yml)

## Security

See [SECURITY.md](SECURITY.md) for how to report vulnerabilities.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Sean McDonnell.
