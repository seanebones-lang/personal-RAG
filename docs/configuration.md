# Configuration

PersonalRAGVault reads settings from **environment variables**. Copy [`.env.example`](../.env.example) to `.env` in the project root for local overrides (do not commit `.env`).

## Variable reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PRV_DB_PATH` | `~/.personalragvault/chroma` | ChromaDB persistence directory |
| `PRV_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Hugging Face / ST model id |
| `PRV_EMBED_PRESET` | `mini` (when no explicit model) | Preset id (`mini`, `bge-small`, …); see `models list` |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API base URL |
|| `OLLAMA_MODEL` | `llama3.2:1b` | Model name for `ollama chat` |
| `PRV_LLM_PROVIDER` | `ollama` | Answer generation provider: `ollama` (local) or `openai` (external OpenAI-compatible endpoint) |
| `PRV_OPENAI_BASE_URL` | `https://integrate.api.nvidia.com/v1` | External endpoint used only when `PRV_LLM_PROVIDER=openai` |
| `PRV_OPENAI_MODEL` | `deepseek-ai/deepseek-v4-flash-0731` | External model used only when `PRV_LLM_PROVIDER=openai` |
| `PRV_OPENAI_API_KEY` | _(unset)_ | External-provider key; falls back to `NVIDIA_API_KEY` |
| `PRV_MAX_FILE_BYTES` | `52428800` (50 MiB) | Skip files larger than this |
| `PRV_CHUNK_STRATEGY` | `char` | `char`, `recursive`, `prose`, `semantic_embed` (`semantic` → `prose`) |
| `PRV_CHUNK_STRATEGY_BY_EXT` | _(empty)_ | e.g. `.md:recursive,.py:recursive` |
| `PRV_SEMANTIC_THRESHOLD` | `0.5` | Similarity breakpoint for `semantic_embed` (0–1) |
| `PRV_CHUNK_SIZE` | `800` | Characters per chunk (min 100); used by `char` strategy |
| `PRV_CHUNK_OVERLAP` | `120` | Overlap between chunks (must be &lt; chunk size) |
| `PRV_CHUNK_MIN_SIZE` | `200` | Min size for `recursive` / `semantic` |
| `PRV_CHUNK_MAX_SIZE` | `800` | Max size for `recursive` / `semantic` |
| `PRV_MAX_CONTEXT_CHARS` | `12000` | Max retrieved text supplied to the configured generation provider |
| `PRV_MAX_TOP_K` | `50` | Upper bound for CLI `--top-k` |
| `PRV_EMBED_BATCH_SIZE` | `32` | Embeddings per encoder batch |
| `PRV_INGEST_BATCH_SIZE` | `500` | Chunks per embed+upsert wave during streaming ingest (min 10) |
| `PRV_INGEST_EXCLUDE_DIRS` | _(empty)_ | Extra directory **names** merged into the built-in skip set for **recursive** discovery (comma-separated, matched against any path component under the ingest root). Built-ins: `.obsidian`, `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox`, `.hg`, `.svn`, `.idea`, `.vscode`. Example: `vendor,dist,.trash` |
| `PRV_USE_FILE_CACHE` | `true` | Skip unchanged files on re-ingest |
| `PRV_USE_FTS` | `true` | Maintain SQLite FTS5 sidecar; **hybrid search uses FTS ranks** (BM25 in-memory only as fallback) |
| `PRV_USE_EMBEDDING_CACHE` | `true` | Cache embeddings by chunk content hash |
| `PRV_HYBRID` | `false` | Default hybrid (vector + FTS/BM25 RRF). Surfaces as `Settings.hybrid_default`. **API:** `POST /query` uses this when the client omits `hybrid`. **CLI/UI:** `--hybrid` / checkbox |
| `PRV_QUERY_PRESET` | _(unset)_ | Default query preset: `fast` \| `balanced` \| `quality` (see CLI `presets`). Applied when flags would otherwise stay off |
| `PRV_HYBRID_FETCH_LIMIT` | `5000` | Cap for BM25 fallback corpus fetch and hybrid candidate width |
| `PRV_HYBRID_RRF_K` | `60` | RRF constant for hybrid / multi-query fusion |
| `PRV_HNSW_SEARCH_EF` | `100` | Chroma HNSW search breadth (higher = slower, more accurate) |
| `PRV_HNSW_M` | `16` | Chroma HNSW graph degree |
| `PRV_MULTI_QUERY` | `false` | Fuse multiple query variants (RRF); composes with hybrid when both on |
| `PRV_EXPAND_QUERY_OLLAMA` | `false` | Ollama rewrites for multi-query |
| `PRV_RERANK` | `false` | Cross-encoder rerank (cached in-process) |
| `PRV_RERANK_CANDIDATES` | `20` | Candidates to rerank before top-k trim |
| `PRV_PARENT_EXPAND` | `false` | Merge neighboring chunks by `parent_id` (metadata filter, not full scan) |
| `PRV_RESPONSE_CACHE` | `true` | Cache non-stream query answers (invalidated on ingest/purge) |
| `PRV_RESPONSE_CACHE_TTL` | `3600` | Response cache TTL in seconds (min 1) |
| `PRV_RESPONSE_CACHE_MAX` | `1000` | Max cached query entries (min 1) |
| `PRV_API_TOKEN` | _(unset)_ | Optional bearer token for HTTP API. **Off by default** (local-first). Constant-time compare. When set, all routes require Bearer **except** `/health` and `/version` |
| `PRV_API_ALLOW_OUTSIDE_HOME` | `false` | When true, API may honor `allow_outside_home` on `/ingest` |

## Examples

**Use a different Ollama model:**

```bash
export OLLAMA_MODEL=mistral
personalragvault query "hello"
```

**Explicitly opt in to an external generation provider:**

```bash
export PRV_LLM_PROVIDER=openai
export PRV_OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
export PRV_OPENAI_MODEL=deepseek-ai/deepseek-v4-flash-0731
export PRV_OPENAI_API_KEY=your-key
personalragvault query "hello"
```

This sends the retrieved context for generated answers to the configured endpoint. Use `--no-llm` to keep a query retrieval-only and make no generation-provider request.

**Store the vault on an external drive:**

```bash
export PRV_DB_PATH=/Volumes/Backup/personalragvault/chroma
personalragvault status
```

**Smaller chunks for short notes:**

```bash
export PRV_CHUNK_SIZE=400
export PRV_CHUNK_OVERLAP=50
personalragvault reindex ~/Documents/notes --yes
```

**Default hybrid retrieval + skip vendor trees on ingest:**

```bash
export PRV_HYBRID=true
export PRV_INGEST_EXCLUDE_DIRS=vendor,dist,.trash
personalragvault ingest ~/Documents/Vault --recursive
personalragvault query "meeting notes" --no-llm   # hybrid on via env
```

**Optional API token (only if binding beyond localhost):**

```bash
export PRV_API_TOKEN=change-me
personalragvault serve --host 127.0.0.1 --port 8765
curl -H "Authorization: Bearer change-me" http://127.0.0.1:8765/health
```

## Changing the embedding model

If you change `PRV_EMBED_MODEL`, existing vectors are **not compatible** with the new model. Purge and re-ingest:

```bash
personalragvault purge --yes
personalragvault ingest ~/Downloads
```

## Validation errors

Settings are validated at startup (via `src/config.py`):

- `PRV_CHUNK_OVERLAP` must be less than `PRV_CHUNK_SIZE`
- `PRV_LLM_PROVIDER` must be `ollama` or `openai`
- Integer env vars must parse and meet minimum bounds

Invalid config raises `ValueError` with a clear message.

## Telemetry

Chroma anonymized telemetry is disabled in code. `ANONYMIZED_TELEMETRY=False` is also set when opening the client.
