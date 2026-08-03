# Changelog

All notable changes to PersonalRAGVault are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2026-08-03

### Added
- Ingest: skip built-in noise dirs (`.obsidian`, `.git`, `.venv`, `node_modules`, caches, …) during recursive discovery
- Ingest: optional extra exclude dir names via `PRV_INGEST_EXCLUDE_DIRS` (comma-separated)
- Query defaults: `PRV_HYBRID` for CLI (`--hybrid/--no-hybrid`), API, and Streamlit UI
- API: `GET /version` + optional `PRV_API_TOKEN` bearer guard (off by default)
- CLI: `graph` — wikilink neighbors + `--export-edges` JSON from vault metadata
- Status shows `hybrid_default` and ingest exclude dir count
- Expanded API unit tests (mocked query/ingest, auth, validation)
- Parser registry: multi-parser per extension so Notion no longer shadows Obsidian `.md` (wikilinks restored)

### Improved
- Serve: OpenAPI URL print + stronger non-loopback security warning
- CI: `ruff check src tests`; `pytest -m "not integration"` with coverage term report
- Docs: configuration + CLI reference for hybrid, excludes, API token, global `-q`

## [1.3.0] - 2026-07-31

### Fixed
- **Critical:** `run_query` dropped `hybrid` / `use_llm` parameters after response-cache wiring — CLI, UI, eval, and benchmarks would crash or mis-route retrieval
- Cache keys now include hybrid, filters, rerank, parent-expand, and max_distance (not just top_k)

### Added
- `personalragvault serve` — local FastAPI HTTP API (`/health`, `/status`, `/query`, `/ingest`, `/cache/*`)
- Streaming batch ingest: per-file process → embed → upsert (`PRV_INGEST_BATCH_SIZE`)
- `ingest --dry-run` file/chunk estimates without writing
- Rich progress for multi-batch embedding and CLI ingest
- Query response cache (`PRV_RESPONSE_CACHE`, TTL, max size); invalidated on ingest/purge
- EPUB parser (optional `ebooklib`+bs4; stdlib zip/html fallback)
- Obsidian wikilink extraction (`wikilinks`, `wikilink_count` metadata)
- Tests: API, response cache, EPUB, wikilinks; pytest `pythonpath`; pytest-cov + httpx dev deps

### Improved
- Large vaults guide: ingest streaming section
- CLI `status` shows response cache stats
- Docs: CLI reference, roadmap, Obsidian source guide, `.env.example`

## [1.2.0] - 2026-06-02

### Added
- **Major ingestion expansion**:
  - iCalendar (.ics) parser for calendar events and meetings
  - Full browser bookmark support: Chrome/Edge HTML exports + Raindrop.io + Pinboard
  - WhatsApp chat export parser (very common personal messaging data)
  - Basic Notion Markdown export parser with property extraction
- Streaming responses now available in the Streamlit UI (token-by-token)
- `personalragvault rerankers list` + preset system (`tiny` / `mini` / `bge`)

### Improved
- Reranking UX: Easy preset system via `PRV_RERANK_PRESET`
- Significantly expanded "Large Vaults" guide with real performance benchmarks
- `personalragvault doctor` now gives better scaling advice at higher vault sizes

### Changed
- Version bumped to 1.2.0 to reflect the substantial increase in personal data source coverage and UX improvements.

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
