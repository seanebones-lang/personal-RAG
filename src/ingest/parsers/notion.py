"""Notion export parser.

Notion exports (Markdown + CSV) contain rich personal knowledge.

This parser focuses on:
- Markdown pages (often with Notion-specific frontmatter)
- Basic extraction of page title and properties when available

Most Notion Markdown content will also be picked up by the generic Markdown parser.
This parser adds better metadata for Notion-specific exports.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument


class NotionParser(BaseParser):
    """Parser for Notion Markdown exports."""

    extensions = frozenset({".md"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        # Look for Notion-style frontmatter or export markers
        if not self._looks_like_notion_export(content, file_path):
            return []

        # Extract title (first H1 or filename)
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file_path.stem

        # Try to extract properties from Notion export format
        properties = self._extract_notion_properties(content)

        text = content
        if title and title not in content[:200]:
            text = f"Title: {title}\n\n{content}"

        return [
            ExtractedDocument(
                text=text,
                extra_metadata={
                    "format": "notion",
                    "platform": "notion",
                    "title": title[:300],
                    **properties,
                },
            )
        ]

    def _looks_like_notion_export(self, content: str, file_path: Path) -> bool:
        # Heuristics for Notion exports
        notion_markers = [
            "Notion",
            "Created time",
            "Last edited time",
            "Tags::",
        ]
        if any(marker.lower() in content.lower() for marker in notion_markers):
            return True

        # Check parent folder structure (Notion exports often have specific naming)
        if "notion" in str(file_path.parent).lower():
            return True

        return False

    def _extract_notion_properties(self, content: str) -> dict:
        props = {}
        # Look for common Notion property patterns in frontmatter or body
        created = re.search(r"Created time::?\s*([^\n]+)", content, re.IGNORECASE)
        if created:
            props["created"] = created.group(1).strip()[:100]

        last_edited = re.search(r"Last edited time::?\s*([^\n]+)", content, re.IGNORECASE)
        if last_edited:
            props["last_edited"] = last_edited.group(1).strip()[:100]

        tags = re.search(r"Tags::?\s*([^\n]+)", content, re.IGNORECASE)
        if tags:
            props["tags"] = tags.group(1).strip()[:200]

        return props
