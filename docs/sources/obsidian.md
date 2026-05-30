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

`[[wikilink]]` resolution is not automated in v0.3; links remain as plain text in chunks.
