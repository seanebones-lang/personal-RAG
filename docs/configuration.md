# Configuration

PersonalRAGVault reads settings from **environment variables**. Copy [`.env.example`](../.env.example) to `.env` in the project root for local overrides (do not commit `.env`).

## Variable reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PRV_DB_PATH` | `~/.personalragvault/chroma` | ChromaDB persistence directory |
| `PRV_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Hugging Face / ST model id |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `llama3.2` | Model name for `ollama chat` |
| `PRV_MAX_FILE_BYTES` | `52428800` (50 MiB) | Skip files larger than this |
| `PRV_CHUNK_SIZE` | `800` | Characters per chunk (min 100) |
| `PRV_CHUNK_OVERLAP` | `120` | Overlap between chunks (must be &lt; chunk size) |
| `PRV_MAX_CONTEXT_CHARS` | `12000` | Max retrieved text sent to Ollama |
| `PRV_MAX_TOP_K` | `50` | Upper bound for CLI `--top-k` |

## Examples

**Use a different Ollama model:**

```bash
export OLLAMA_MODEL=mistral
personalragvault query "hello"
```

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

## Changing the embedding model

If you change `PRV_EMBED_MODEL`, existing vectors are **not compatible** with the new model. Purge and re-ingest:

```bash
personalragvault purge --yes
personalragvault ingest ~/Downloads
```

## Validation errors

Settings are validated at startup (via `src/config.py`):

- `PRV_CHUNK_OVERLAP` must be less than `PRV_CHUNK_SIZE`
- Integer env vars must parse and meet minimum bounds

Invalid config raises `ValueError` with a clear message.

## Telemetry

Chroma anonymized telemetry is disabled in code. `ANONYMIZED_TELEMETRY=False` is also set when opening the client.
