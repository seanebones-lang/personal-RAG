# Working with Large Vaults

As your personal knowledge base grows beyond a few thousand chunks, retrieval quality and performance require more deliberate tuning. This guide consolidates the best practices that have emerged from real-world use of PersonalRAGVault.

> **Tip**: Run `personalragvault doctor` regularly. It now contains dynamic recommendations based on your current vault size.

## When Does "Large" Start?

| Vault Size     | Recommendation Level | Typical Symptoms |
|----------------|----------------------|------------------|
| < 5,000 chunks | Normal               | Everything works well with defaults |
| 5k – 15k       | Medium               | Occasional slow queries, noisier results |
| 15k – 30k      | High                 | Noticeable latency, benefit from hybrid search |
| 30k – 60k+     | Very High            | Requires active tuning and maintenance |
| 100k+          | Extreme              | Consider architectural changes |

## Core Strategies

### 1. Use Metadata Filtering Aggressively

The single most effective technique for large vaults is **not** retrieving better — it is retrieving *less*.

Prefer these over pure semantic search:

```bash
personalragvault query "Q3 strategy notes" \
  --where-year 2025 \
  --source-contains "work/strategy"
```

Key metadata fields you can filter on:
- `year`
- `source` / `file_name`
- `extension`
- Custom fields from parsers (e.g. `chat_name`, `event_start`)

See [Filtering](filtering.md) for the full syntax.

### 2. Hybrid Search Becomes Essential

Once you pass ~12–15k chunks, pure vector search starts to degrade in both quality and speed.

Recommended default for large vaults:

```bash
export PRV_HYBRID=true          # or pass --hybrid on queries
export PRV_HYBRID_FETCH_LIMIT=3000   # lower this for very large vaults
```

Hybrid search (BM25 + vector + RRF) is dramatically more robust on noisy, large collections.

### 3. Chunking Strategy Matters More at Scale

| Strategy         | Best For                          | Cost at Scale          | Recommendation |
|------------------|-----------------------------------|------------------------|----------------|
| `char`           | General use                       | Low                    | Default for most people |
| `prose`          | Long-form notes, articles         | Medium                 | Good middle ground |
| `semantic_embed` | High-precision research vaults    | **High**               | Only use on <10k chunk vaults unless you have measured gains |
| `recursive`      | Code-heavy or structured data     | Low–Medium             | Excellent for codebases |

**Rule of thumb**: The larger your vault, the more conservative you should be with `semantic_embed`.

### 4. Maintenance Routines

Large vaults require regular housekeeping:

```bash
# Weekly / bi-weekly
personalragvault compact

# After major life events (new job, big project, travel)
personalragvault reindex ~/important-folder --force
```

`compact` rebuilds sidecar indexes and removes orphaned cache entries. It becomes increasingly important as your collection grows.

### 5. Reranking Trade-offs

Reranking improves precision but adds significant latency at scale.

**Guidelines**:

- **< 10k chunks**: Safe to leave `--rerank` on by default.
- **15k–40k chunks**: Use reranking only on high-stakes queries or via a dedicated "deep search" alias.
- **> 40k chunks**: Prefer metadata filtering + hybrid over reranking in most cases.

Use lightweight presets for better CPU performance:

```bash
export PRV_RERANK_PRESET=tiny     # fastest
# or
export PRV_RERANK_PRESET=mini     # balanced (default)
```

You can control reranker aggressiveness with:

```bash
export PRV_RERANK_CANDIDATES=12   # lower = faster
```

See `personalragvault rerankers list` for available presets.

### 6. HNSW Tuning

For very large collections, the default HNSW parameters may be suboptimal:

```bash
export PRV_HNSW_SEARCH_EF=200     # higher = better recall, slower
export PRV_HNSW_M=32              # only change at ingest time
```

Increasing `search_ef` is usually the first knob to turn when recall feels poor on large vaults.

### 7. When to Split Your Vault

At a certain point, one giant vault stops being the right architecture.

Consider splitting when:

- You have clearly separate domains (Work vs Personal vs Research)
- Query latency becomes unacceptable even with hybrid + filters
- You want different embedding models or chunking strategies per domain

You can run multiple independent vaults simply by setting different `PRV_DB_PATH` values.

Example:

```bash
# Work vault
PRV_DB_PATH=~/.personalragvault/work personalragvault ingest ~/Work

# Personal vault
PRV_DB_PATH=~/.personalragvault/personal personalragvault ingest ~/Documents
```

### 8. When to Consider Other Tools

PersonalRAGVault is optimized for **single-user, local, < 100k chunks** use cases.

If you regularly exceed these characteristics, you may eventually benefit from:

- **LanceDB** or **Chroma** with better quantization
- **pgvector** + PostgreSQL
- **Typesense** or **Meilisearch** (excellent hybrid search)
- Full enterprise RAG frameworks (LlamaIndex workflows, Haystack, etc.)

The `doctor` command will start suggesting external tools once you cross ~60k chunks.

## Recommended Configurations by Size

### Medium Vault (8k–20k chunks)

```bash
export PRV_HYBRID=true
export PRV_RERANK=false          # or only enable selectively
export PRV_CHUNK_STRATEGY=prose
```

### Large Vault (20k–50k chunks)

```bash
export PRV_HYBRID=true
export PRV_HYBRID_FETCH_LIMIT=4000
export PRV_RERANK=false
export PRV_HNSW_SEARCH_EF=150
```

Run `compact` every 1–2 weeks.

### Very Large Vault (50k+ chunks)

- Heavy use of metadata filtering
- Hybrid search as default
- Minimal or no reranking
- Regular `compact` + periodic `reindex` of active folders only
- Consider splitting the vault

## Monitoring Your Vault

Use these commands regularly:

```bash
personalragvault status
personalragvault doctor
```

Pay attention to:
- Chunk count growth rate
- Sidecar cache sizes
- Query timing (now shown after every query in the CLI)

---

**Next Steps**

- Start with the recommendations from `personalragvault doctor`
- Experiment with hybrid + metadata filtering on your largest folders
- Come back and reread this guide once you cross 15k chunks

If you have real-world numbers (chunk count, typical query latency, data sources) from a large vault, we would love to hear about them in the issues — they help improve this guidance for everyone.

## Benchmarks & Measurements (2026)

All numbers below were measured on an Apple M2 MacBook Pro (16 GB unified memory) using the built-in benchmarking script (`python scripts/benchmark.py`).

### Query Latency by Retrieval Mode (small vault, ~few hundred chunks)

| Mode      | Avg (ms) | P95 (ms) | Notes |
|-----------|----------|----------|-------|
| Vector only | 208     | 1014    | Pure embedding similarity |
| Hybrid    | 157     | 1207    | BM25 + vector + RRF (recommended default) |
| + Rerank  | 338     | 1000    | Hybrid + cross-encoder rerank (top 20 candidates) |

**Observations**:
- Hybrid search can be *faster* than pure vector in some cases due to better early termination.
- Reranking adds ~2x latency in this environment but significantly improves precision on ambiguous queries.
- P95 spikes are often caused by first-time model loading or cache misses.

### Ingestion Throughput (synthetic data)

| Strategy   | ~Chunks | Est. time (wall) | Notes |
|------------|---------|------------------|-------|
| `char`     | 5,000   | ~45–70s         | Fastest, simplest |
| `prose`    | 5,000   | ~60–90s         | Good balance (recommended for most users) |
| `semantic_embed` | 5,000 | ~3–5 min     | Much slower due to per-sentence embedding |

### Memory Considerations

- Embedding model (`all-MiniLM-L6-v2`): ~90–120 MB resident
- Cross-encoder reranker (MiniLM): ~150–200 MB when loaded
- Chroma HNSW index: Roughly 1.2–1.8× the size of the raw text + embeddings

**Rule of thumb**: Keep at least 4–6 GB free RAM for comfortable operation with 20k+ chunk vaults when using reranking.

### Larger Vault Projections (Estimates)

These are extrapolated from smaller runs + Chroma behavior:

| Vault Size | Recommended Config                  | Expected Query Latency (P95) | Notes |
|------------|-------------------------------------|------------------------------|-------|
| 15k chunks | Hybrid + `search_ef=150`           | 400–900 ms                  | Still very usable |
| 30k+ chunks| Hybrid + metadata filters + `compact` regularly | 600–1500 ms | Rerank only on demand |
| 60k+ chunks| Heavy filtering + consider splitting vault | 1–3s+ with rerank | Time to split or move to stronger backend |

> **Important**: Your mileage will vary significantly based on document length, chunking strategy, disk speed (SSD vs HDD), and whether models are cached.

Run the benchmark script on your own machine with your actual data for the most relevant numbers.