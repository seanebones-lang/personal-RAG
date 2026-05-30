# Changelog

All notable changes to PersonalRAGVault are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-05-30

### Added

- Streamlit UI components: result cards, conversation history, document preview
- `personalragvault eval run` with Hit@k and MRR ([docs/evaluation.md](docs/evaluation.md))
- Chunk strategies: `PRV_CHUNK_STRATEGY=char|recursive|semantic` with markdown/code rules
- Chroma HNSW tuning via `PRV_HNSW_SEARCH_EF` and `PRV_HNSW_M`
- Embedding cache (`PRV_USE_EMBEDDING_CACHE`) and paginated hybrid corpus fetch
- Telegram export parser (`result.json`) and Obsidian frontmatter/tags
- Source guides in [docs/sources/](docs/sources/)

## [0.2.0] - 2026-05-30

### Added

- Embedding presets (`models list`, `PRV_EMBED_PRESET`) and dimension guard
- Parser registry with `.eml` and `.mbox` support
- Rich chunk metadata (year, extension, mtime, relative_path, etc.)
- Query filters: `--where-year`, `--source-contains`, `--extension`, `--filter`
- Hybrid search: `--hybrid` (BM25 + vector RRF)
- File hash cache for faster re-ingest (`PRV_USE_FILE_CACHE`)
- SQLite FTS5 sidecar (`PRV_USE_FTS`) and `compact` command
- `src/core/` shared library for CLI and UI
- Optional Streamlit UI: `pip install personalragvault[ui]` and `personalragvault ui`
- Docs: [docs/roadmap.md](docs/roadmap.md), [docs/filtering.md](docs/filtering.md)

### Added (0.1.x foundation)

- Production-ready CLI: chunking, stable IDs, upsert, dedup on re-ingest
- Commands: `status`, `purge`, `reindex`, `watch`
- Environment-based configuration (`src/config.py`, `.env.example`)
- Extended file types (DOCX, code, markup)
- `--recursive`, `--allow-outside-home`, `--no-llm`, global `--verbose`/`--quiet`/`--debug`
- Test suite and GitHub Actions CI (Python 3.10, 3.12)
- Full documentation in `docs/`
- `personalragvault` console script via `pyproject.toml`

### Fixed

- Crash on invalid ingest paths
- Chroma query when `top_k` exceeds collection size
- Hardcoded Ollama model; configurable host and preflight check

## [0.1.0] - 2026-05-30

### Added

- Initial ingest → embed → Chroma → query loop
- Basic PDF/TXT/MD/JSON support
- Ollama integration for answers

[Unreleased]: https://github.com/seanebones-lang/personal-RAG/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/seanebones-lang/personal-RAG/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/seanebones-lang/personal-RAG/releases/tag/v0.1.0
