# Changelog

All notable changes to PersonalRAGVault are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- iCalendar (.ics) parser — first-class support for calendar events and meetings (very high-value personal data)
- Significantly expanded large-vault guidance inside `personalragvault doctor`

### Improved
- Reranking discoverability (better hints in `models list` and configuration)
- Demo / community contribution section in README

## [1.1.0] - 2026-06-01

### Added
- **Reliability**: `personalragvault doctor` — full health checks including critical embedding dimension consistency detection
- **Configuration**: `personalragvault config edit` + proper TOML config file support (`~/.personalragvault/config.toml` or `PRV_CONFIG_PATH`)
- **UX**: Streaming answers in CLI (token-by-token via Ollama)
- **Grounding**: Source-tagged context + automatic citation extraction and display in both CLI and UI
- **Multi-turn**: Real conversation history passed to the LLM for follow-up questions (CLI + UI)
- **Ingestion**: Optional OCR support via `pip install "personalragvault[ocr]"` (images + basic scanned documents)
- **Observability**: Per-query timing breakdown (retrieval / generation / total)
- **Safety**: Strong runtime warnings when using expensive chunking strategies (e.g. `semantic_embed`)

### Changed
- `build_tagged_context` is now the default context builder for LLM generation
- `run_query` now supports `stream=True` for streaming generation
- Improved prompt engineering to encourage proper source citation

### Improved
- Much better developer and power-user experience (doctor, config, timing, citations)
- Significantly improved perceived performance with streaming
- More robust handling when users change embedding models

## [1.0.0] - 2026-05-30

### Added

- Eval: NDCG@k, `personalragvault eval generate` for synthetic datasets
- Chunking: `semantic_embed`, `prose` alias, `PRV_CHUNK_STRATEGY_BY_EXT`, `--chunk-strategy` on ingest
- Retrieval: `--multi-query`, `--expand-query`, `--rerank`, `--parent-expand` (+ env defaults)
- Metadata `parent_id` for parent-document expansion
- UI: `st.chat_input` chat layout, history restore, excerpt highlighting, JSON/Markdown export
- CLI: `query --output` JSON export
- Docs: [community.md](docs/community.md), [assets/DEMO.md](docs/assets/DEMO.md)

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
