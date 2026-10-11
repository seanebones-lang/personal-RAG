# Try PersonalRAGVault with a synthetic sample

This first-use walkthrough proves a small local search path. It does not measure
retrieval quality across other collections or validate generated answers.

## Install and run

Use Git and Python 3.10–3.12 on macOS or Linux:

```bash
git clone --branch v1.5.1 --depth 1 https://github.com/seanebones-lang/personal-RAG.git
cd personal-RAG
./scripts/setup.sh --ui
./scripts/try-demo.sh
```

The script only ingests `docs/assets/demo-sample`, which contains fictional notes.
It selects the MiniLM embedding model, uses a separate `.demo-vault/chroma` index,
and performs a hybrid search without calling a generation provider. No account,
API key, or Ollama installation is needed. Python dependencies and the first
embedding-model download require internet access. Re-running the demo force-updates
only those sample sources; it does not purge an index.

## Inspect the result

The question is “What was the January invoice total?” A result should contain:

- The fictional supplier **Acme Corp**.
- The amount **$1,240.50**.
- A source path ending in `docs/assets/demo-sample/notes.md`.

The CLI prints source text rather than a generated answer. The note mentions an
invoice filename; no invoice PDF is included. A retrieved passage is evidence of
what the sample says, not verification of a real transaction.

## Try the browser interface

```bash
source .venv/bin/activate
PRV_DB_PATH="$PWD/.demo-vault/chroma" PRV_LLM_PROVIDER=ollama personalragvault ui
```

Open `http://127.0.0.1:8501`:

1. **Status:** confirm that the sample index has chunks.
2. **Query:** select **Retrieval only (do not call generation provider)**.
3. Enter the invoice question and inspect the result's source and text.
4. Select the source preview to read the surrounding fictional notes.
5. Optionally enable hybrid search and compare results. Do not treat the ranking
   or a distance score as a calibrated confidence that an answer is true.

The command binds the UI to localhost. It is a local interface, not a public hosted
service. Close it with Ctrl+C in the terminal that started it.

## Move to your own files

Open a new shell or unset `PRV_DB_PATH` to return to the default personal index.
Choose a small folder, preview it with `ingest --dry-run`, then ingest deliberately.
Follow [getting started](getting-started.md). To use generated answers, configure
local Ollama or explicitly select an external endpoint. External generated-answer
requests send retrieved context to that provider; retrieval-only mode skips them.

Report installation failures, poor matches, or confusing steps in
[GitHub issues](https://github.com/seanebones-lang/personal-RAG/issues). Include your
OS, Python version, and a minimal synthetic reproduction. Keep private files and
credentials out of reports.
