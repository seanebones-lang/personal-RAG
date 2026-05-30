#!/usr/bin/env bash
# Local demo for screenshots — isolated vault + sample docs.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

export PRV_DB_PATH="${PRV_DB_PATH:-$ROOT/.demo-vault/chroma}"
SAMPLE="$ROOT/docs/assets/demo-sample"

if [[ ! -d "$ROOT/.demo-vault/chroma" ]] || [[ "$(personalragvault status 2>/dev/null | grep 'Documents' | awk '{print $3}')" == "0" ]]; then
  echo "==> Ingesting demo sample into $PRV_DB_PATH"
  personalragvault ingest "$SAMPLE" --allow-outside-home
fi

echo "==> Open http://127.0.0.1:8501"
echo "    Suggested query: What was the January invoice total?"
echo "    Try: Hybrid search, Preview source on a result card"
exec personalragvault ui --port 8501
