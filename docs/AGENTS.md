# Specialized agents — PersonalRAGVault full-stack swarm

Root: `/Users/nexteleven/Desktop/personal-RAG`  
Branch: `main`  
Do **not** commit from children — orchestrator integrates.

## Roster

| ID | Role | Owns (only) | Forbidden |
|----|------|-------------|-----------|
| **CORE** | Ingest + config + vault query defaults | `src/ingest/ingest.py`, `src/config.py`, `src/core/vault.py` (defaults only), `tests/test_ingest.py`, `tests/test_config.py`, new `tests/test_discover_excludes.py` | `src/query/**`, `src/ui/**`, CI, docs except if needed |
| **API** | FastAPI serve surface | `src/query/api.py`, `src/cli.py` (serve command only), `tests/test_api.py`, `.env.example` API keys section | `src/ingest/**`, deep retrieval rewrites |
| **QA** | CI + docs + coverage glue | `.github/workflows/ci.yml`, `docs/configuration.md`, `docs/cli-reference.md`, `CHANGELOG.md` (Unreleased), `docs/roadmap.md` touch, `Makefile` if needed | Core retrieval algorithms, license relicense |
| **ORCH** | Integrate, ruff/pytest, commit/push, next wave | Everything at merge | N/A |

## Wave assignment

- Wave 1: CORE (W1.1–W1.4) ∥ API starts W2.1–W2.3 ∥ QA drafts W3.1 + docs stubs
- Wave 2+: ORCH fills gaps; optional GRAPH agent for W4 if CORE free

## Child rules

1. `cd /Users/nexteleven/Desktop/personal-RAG && pwd && ls -la && git status`
2. Prefer minimal diffs; keep `run_query(hybrid=, use_llm=)` contract
3. Verify with `.venv/bin/ruff check src tests` and `.venv/bin/pytest -m "not integration"`
4. No network model downloads in unit tests
5. Hand off file list + verify cmds; no git commit
