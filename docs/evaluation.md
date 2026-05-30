# Retrieval evaluation

Measure how well your vault retrieves the right sources before tuning chunk size, hybrid search, or embedding presets.

## Dataset format

Create a JSONL file (one JSON object per line):

```json
{"question": "January invoice total", "expected_source_contains": "invoice.pdf", "optional_year": 2025}
{"question": "meeting notes", "expected_source_contains": "notes.md", "generated": true}
```

| Field | Required | Description |
|-------|----------|-------------|
| `question` | yes | Query text |
| `expected_source_contains` | yes | Substring matched against `source` or `file_name` metadata |
| `optional_year` | no | Applies `--where-year` filter for that case |
| `generated` | no | Set by `eval generate`; review before trusting |

Keep datasets local. Do not commit personal eval files to public repos.

## Run evaluation

```bash
personalragvault eval run --dataset ./my_eval.jsonl
personalragvault eval run --dataset ./my_eval.jsonl --hybrid --top-k 10
personalragvault eval run --dataset ./my_eval.jsonl --multi-query --rerank
personalragvault eval run --dataset ./my_eval.jsonl --output results.json
```

## Metrics

| Metric | Meaning |
|--------|---------|
| **Hit@k** | Fraction of questions where any top-k chunk matches the expected source |
| **MRR** | Mean reciprocal rank of the first matching chunk |
| **NDCG@k** | Normalized discounted cumulative gain (binary relevance per rank) |

## Synthetic dataset generation

Sample chunks from your vault (or a folder) and optionally ask Ollama for questions:

```bash
personalragvault eval generate --output ./draft_eval.jsonl --sample 20
personalragvault eval generate ~/Documents/notes --output ./draft.jsonl --no-llm
```

**Always review** generated rows before using them for tuning. Rows include `"generated": true`.

## Building a dataset manually

1. Ingest your folder.
2. Run queries you care about and note which file answered each question.
3. Add one JSONL row per question with the filename substring you expect.

## Example fixture

See [`tests/fixtures/sample_eval.jsonl`](../tests/fixtures/sample_eval.jsonl).
