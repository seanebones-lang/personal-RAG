# Telegram exports

PersonalRAGVault ingests [Telegram Desktop](https://desktop.telegram.org/) JSON exports.

## Export steps

1. Open Telegram Desktop.
2. Open the chat you want to export.
3. Menu → **Export chat history**.
4. Format: **JSON** (not HTML-only).
5. Export to a folder containing `result.json`.

## Ingest

```bash
personalragvault ingest /path/to/export/folder --recursive
```

Only files named `result.json` are parsed as Telegram messages. Other `.json` files use the generic text path.

## Metadata stored

- `platform`: `telegram`
- `chat_name`, `message_from`, `message_date`, `message_index`

Use filters: `personalragvault query "..." --source-contains TelegramExportFolder`
