"""Pinboard.in export parser.

Supports Pinboard JSON exports (https://pinboard.in/export/).

Typical Pinboard JSON structure:
[
  {
    "description": "Title",
    "extended": "Notes...",
    "href": "https://...",
    "tags": "tag1 tag2",
    "time": "2024-05-31T12:34:56Z",
    "shared": "yes",
    "toread": "no"
  }
]
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument


class PinboardParser(BaseParser):
    """Parser for Pinboard JSON exports."""

    extensions = frozenset({".json"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        if not file_path.name.lower().endswith(".json"):
            return []

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(data, list):
            return []

        docs: List[ExtractedDocument] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            url = item.get("href") or item.get("url") or ""
            title = item.get("description") or item.get("title") or url

            if not url:
                continue

            tags = item.get("tags", "").split() if item.get("tags") else []

            created = item.get("time") or item.get("created") or ""
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    created = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

            notes = item.get("extended", "").strip()

            text = f"Bookmark: {title}\nURL: {url}"
            if tags:
                text += f"\nTags: {', '.join(tags)}"
            if created:
                text += f"\nAdded: {created}"
            if notes:
                text += f"\n\n{notes}"

            docs.append(
                ExtractedDocument(
                    text=text,
                    extra_metadata={
                        "format": "pinboard",
                        "title": str(title)[:500],
                        "url": url,
                        "tags": ", ".join(tags)[:300] if tags else "",
                        "date_added": created,
                        "platform": "pinboard",
                        "notes": notes[:1000] if notes else "",
                    },
                )
            )

        return docs
