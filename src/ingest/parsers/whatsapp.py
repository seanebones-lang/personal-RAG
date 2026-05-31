"""WhatsApp chat export parser.

Supports the standard WhatsApp text export format (both individual and group chats).

Typical format:
DD/MM/YYYY, HH:mm - Sender: Message text
DD/MM/YYYY, HH:mm - Sender: <Media omitted>

Also supports the full export where the chat file is named _chat.txt inside a folder.

Extracts:
- Timestamp
- Sender
- Message text
- Media indicators
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument


class WhatsAppParser(BaseParser):
    """Parser for WhatsApp chat exports."""

    extensions = frozenset({".txt"})

    # Common WhatsApp date patterns (various locales)
    DATE_PATTERNS = [
        # DD/MM/YYYY
        r"(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.+?):\s*(.*)",
        # DD-MM-YYYY
        r"(\d{1,2}-\d{1,2}-\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.+?):\s*(.*)",
        # YYYY-MM-DD
        r"(\d{4}-\d{2}-\d{2}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.+?):\s*(.*)",
    ]

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        # Only process files that look like WhatsApp exports
        name = file_path.name.lower()
        if not (name.endswith(".txt") or name == "_chat.txt"):
            return []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        # Try to determine chat name from filename or first line
        chat_name = self._extract_chat_name(file_path, content)

        lines = content.splitlines()
        docs: List[ExtractedDocument] = []
        current_message = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parsed = self._parse_message_line(line)
            if parsed:
                # Save previous message if exists
                if current_message:
                    docs.append(self._create_document(current_message, chat_name))

                current_message = parsed
            elif current_message:
                # Continuation of previous message (multi-line)
                current_message["text"] += "\n" + line

        # Don't forget the last message
        if current_message:
            docs.append(self._create_document(current_message, chat_name))

        return docs

    def _parse_message_line(self, line: str) -> dict | None:
        for pattern in self.DATE_PATTERNS:
            match = re.match(pattern, line)
            if match:
                date_str, time_str, sender, text = match.groups()
                # Normalize date
                date_str = date_str.replace("-", "/")
                try:
                    # Try common formats
                    dt = None
                    for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
                        try:
                            dt = datetime.strptime(f"{date_str} {time_str}", f"{fmt} %H:%M")
                            break
                        except ValueError:
                            continue
                    if not dt:
                        dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%y %H:%M")

                    return {
                        "date": dt,
                        "sender": sender.strip(),
                        "text": text.strip(),
                    }
                except ValueError:
                    continue
        return None

    def _extract_chat_name(self, file_path: Path, content: str) -> str:
        # Try filename first (e.g. "WhatsApp Chat with John Doe.txt")
        name = file_path.stem
        if "chat with" in name.lower():
            return name.split("Chat with", 1)[-1].strip()

        # Try first line
        first_line = content.split("\n", 1)[0]
        if "WhatsApp" in first_line or "chat" in first_line.lower():
            return "WhatsApp Chat"

        return file_path.parent.name or "Unknown Chat"

    def _create_document(self, msg: dict, chat_name: str) -> ExtractedDocument:
        date_str = msg["date"].strftime("%Y-%m-%d %H:%M")
        text = msg["text"]

        header = f"Chat: {chat_name}\nFrom: {msg['sender']}\nDate: {date_str}\n\n"
        full_text = header + text

        return ExtractedDocument(
            text=full_text,
            extra_metadata={
                "format": "whatsapp",
                "platform": "whatsapp",
                "chat_name": chat_name[:200],
                "sender": msg["sender"][:100],
                "message_date": date_str,
                "has_media": "<media" in text.lower() or "omitted" in text.lower(),
            },
        )
