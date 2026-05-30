# Changelog

All notable changes to PersonalRAGVault are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

[Unreleased]: https://github.com/seanebones-lang/probable-fishstick/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/seanebones-lang/probable-fishstick/releases/tag/v0.1.0
