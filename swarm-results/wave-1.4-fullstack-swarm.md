# Full-stack swarm ship — PersonalRAGVault 1.4.0 (2026-08-03)

## Team
- CORE (sw805b1932): ingest excludes + PRV_HYBRID settings
- API (sw235db02c): /version, PRV_API_TOKEN, API tests, serve polish
- QA (sw77ccd6a1): CI + docs + CHANGELOG
- ORCH: integrate, hybrid CLI/UI wiring, graph CLI, Notion/Obsidian registry fix, 1.4.0 release

## Verify
- ruff clean
- pytest -m "not integration" → 92 passed
- E2E: dry-run skips .obsidian; graph hello → Other; status hybrid_default + exclude count

## Stop line
Waves 1–4 closed. W5 ONNX pinned research-only. No further high-leverage eng without demand.
