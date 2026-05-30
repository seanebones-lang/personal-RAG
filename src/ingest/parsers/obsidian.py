"""Obsidian markdown: YAML frontmatter and tags."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TAG_RE = re.compile(r"(?<!\w)#([a-zA-Z0-9_/-]+)")


class ObsidianMarkdownParser(BaseParser):
    """Enrich .md files with Obsidian frontmatter metadata."""

    extensions = frozenset({".md", ".markdown"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        try:
            raw = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        body = raw
        extra: dict = {"format": "obsidian", "platform": "obsidian"}

        match = _FRONTMATTER_RE.match(raw)
        if match:
            fm = match.group(1)
            body = raw[match.end() :]
            for line in fm.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip().lower()
                    val = val.strip().strip('"').strip("'")
                    if key in ("title", "tags", "date", "aliases"):
                        extra[f"fm_{key}"] = val[:500]

        tags = list({m.group(1) for m in _TAG_RE.finditer(body)})[:20]
        if tags:
            extra["obsidian_tags"] = ",".join(tags)

        if not body.strip():
            return []
        return [ExtractedDocument(text=body.strip(), extra_metadata=extra)]
