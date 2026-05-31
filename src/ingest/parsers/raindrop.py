"""Raindrop.io export parser.

Supports Raindrop.io JSON exports (the most common export format).

Raindrop JSON export structure (typical):
[
  {
    "_id": "...",
    "link": "https://...",
    "title": "...",
    "excerpt": "...",
    "tags": ["tag1", "tag2"],
    "created": "2024-...",
    "lastUpdate": "...",
    "collection": { "title": "Folder Name" },
    ...
  }
]
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument


class RaindropParser(BaseParser):
    """Parser for Raindrop.io JSON exports."""

    extensions = frozenset({".json"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        # Only process files that look like Raindrop exports
        if not file_path.name.lower().endswith((".json",)):
            return []

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        # Raindrop exports are typically a list at the top level
        if not isinstance(data, list):
            return []

        docs: List[ExtractedDocument] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            url = item.get("link") or item.get("url") or ""
            title = item.get("title") or item.get("name") or url
            if not url:
                continue

            tags = item.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            folder = ""
            if isinstance(item.get("collection"), dict):
                folder = item["collection"].get("title", "")
            elif isinstance(item.get("folder"), str):
                folder = item["folder"]

            created = item.get("created") or item.get("createdAt") or ""
            if created:
                try:
                    # Raindrop often uses ISO format
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    created = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

            text = f"Bookmark: {title}\nURL: {url}"
            if folder:
                text += f"\nFolder: {folder}"
            if tags:
                text += f"\nTags: {', '.join(tags)}"
            if created:
                text += f"\nAdded: {created}"

            docs.append(
                ExtractedDocument(
                    text=text,
                    extra_metadata={
                        "format": "raindrop",
                        "title": str(title)[:500],
                        "url": url,
                        "folder": str(folder)[:300],
                        "tags": ", ".join(tags)[:300] if tags else "",
                        "date_added": created,
                        "platform": "raindrop",
                    },
                )
            )

        return docs
