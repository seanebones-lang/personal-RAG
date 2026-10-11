#!/usr/bin/env bash
# Run only the repository's synthetic sample, in a separate local demo index.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI="$ROOT/.venv/bin/personalragvault"
if [[ ! -x "$CLI" ]]; then
  echo "First run ./scripts/setup.sh (add --ui for the optional web interface)." >&2
  exit 2
fi
export PRV_DB_PATH="${PRV_DEMO_DIR:-$ROOT/.demo-vault}/chroma"
export PRV_LLM_PROVIDER=ollama
export PRV_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
export PRV_EMBED_PRESET=mini
export PRV_QUERY_PRESET=fast
export PRV_MULTI_QUERY=false
export PRV_EXPAND_QUERY_OLLAMA=false
export PRV_RERANK=false
export PRV_PARENT_EXPAND=false
export PRV_RESPONSE_CACHE=false
export PRV_USE_FTS=true
export PRV_CHUNK_STRATEGY=char
export PRV_CHUNK_SIZE=800
export PRV_CHUNK_OVERLAP=120
export ANONYMIZED_TELEMETRY=False
echo "Synthetic sample only. Demo index: $PRV_DB_PATH"
echo "The first run downloads the embedding model; no generation provider is called."
"$CLI" --quiet ingest "$ROOT/docs/assets/demo-sample" --force
"$CLI" query "What was the January invoice total?" --no-llm --hybrid --top-k 3
