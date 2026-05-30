# Filtered queries

PersonalRAGVault stores metadata on every chunk. Filter at query time with CLI flags or JSON.

## Metadata fields

| Field | Type | Example |
|-------|------|---------|
| `source` | string | Full file path |
| `file_name` | string | `invoice.pdf` |
| `extension` | string | `.pdf` |
| `mtime` | int | Unix epoch |
| `year` | int | `2025` |
| `ingested_at` | int | Unix epoch |
| `relative_path` | string | Path under ingest root |
| `chunk_index` | int | `0` |
| `total_chunks` | int | `3` |
| `format` | string | `eml`, `mbox`, `.pdf` |
| `message_from` | string | Email sender (eml/mbox) |

## CLI examples

```bash
# Chunks from 2025 only
personalragvault query "invoices" --where-year 2025

# Paths containing Downloads
personalragvault query "notes" --source-contains Downloads

# PDFs only
personalragvault query "contracts" --extension pdf

# Combined (AND)
personalragvault query "tax" --where-year 2025 --extension pdf

# Raw Chroma where JSON
personalragvault query "acme" --filter '{"extension": ".pdf"}'
```

Combine with hybrid search:

```bash
personalragvault query "invoice number" --hybrid --where-year 2025
```

## Changing filters after ingest

Re-ingest files to refresh `mtime` / `year`. Parser-specific fields appear when using `.eml` / `.mbox` ingest.

## See also

- [Configuration](configuration.md)
- [CLI reference](cli-reference.md)
