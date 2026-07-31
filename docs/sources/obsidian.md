# Obsidian vaults

Obsidian notes are ingested as `.md` / `.markdown` files with extra metadata.

## Setup

Point ingest at your vault folder (or a subfolder):

```bash
personalragvault ingest ~/Documents/MyVault --recursive
```

## What is extracted

- YAML frontmatter (`title`, `tags`, `date`, `aliases`) → metadata fields `fm_*`
- `#tags` in body → `obsidian_tags`
- Markdown headings used for `section_title` when using recursive/semantic chunking

## Chunking tip

For long notes, use:

```bash
export PRV_CHUNK_STRATEGY=recursive
personalragvault reindex ~/Documents/MyVault --yes
```

## Wikilinks

From v1.3, `[[wikilink]]` and `![[embed]]` targets are extracted into metadata:

- `wikilinks` — comma-separated note names (alias/heading stripped)
- `wikilink_count` — integer edge count

Links still appear as plain text inside chunks (no graph DB yet). You can filter with:

```bash
personalragvault query "related notes" --filter '{"wikilink_count": {"$gte": 1}}'
```
