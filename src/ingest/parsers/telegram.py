"""Telegram Desktop JSON export parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from src.ingest.parsers.base import BaseParser, ExtractedDocument


class TelegramParser(BaseParser):
    extensions = frozenset({".json"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        if file_path.name != "result.json":
            return []
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(data, dict) or "messages" not in data:
            return []

        messages = data.get("messages", [])
        chat_name = str(data.get("name", file_path.parent.name))
        docs: List[ExtractedDocument] = []

        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                continue
            if msg.get("type") != "message":
                continue
            text = _message_text(msg)
            if not text.strip():
                continue
            from_name = str(msg.get("from") or msg.get("from_id") or "")
            date = str(msg.get("date", ""))
            header = f"Chat: {chat_name}\nFrom: {from_name}\nDate: {date}\n\n"
            docs.append(
                ExtractedDocument(
                    text=(header + text).strip(),
                    extra_metadata={
                        "format": "telegram",
                        "platform": "telegram",
                        "chat_name": chat_name[:200],
                        "message_index": idx,
                        "message_from": from_name[:200],
                        "message_date": date[:80],
                    },
                )
            )
        return docs


def _message_text(msg: dict[str, Any]) -> str:
    raw = msg.get("text")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: List[str] = []
        for item in raw:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return ""
