"""Obsidian markdown: YAML frontmatter, tags, and wikilink graph edges."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TAG_RE = re.compile(r"(?<!\w)#([a-zA-Z0-9_/-]+)")
# [[Note]], [[Note|alias]], [[Note#heading]], ![[embed]]
_WIKILINK_RE = re.compile(r"! ?\[\[([^\]]+)\]\]|\[\[([^\]]+)\]\]")


def extract_wikilinks(body: str, limit: int = 40) -> List[str]:
    """Return unique wikilink targets (note names) from markdown body."""
    seen: list[str] = []
    found: set[str] = set()
    for m in _WIKILINK_RE.finditer(body):
        raw = (m.group(1) or m.group(2) or "").strip()
        if not raw:
            continue
        # strip alias and heading/block
        target = raw.split("|", 1)[0].split("#", 1)[0].split("^", 1)[0].strip()
        if not target or target in found:
            continue
        found.add(target)
        seen.append(target)
        if len(seen) >= limit:
            break
    return seen


class ObsidianMarkdownParser(BaseParser):
    """Enrich .md files with Obsidian frontmatter, tags, and wikilink edges."""

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

        links = extract_wikilinks(body)
        if links:
            extra["wikilinks"] = ",".join(links)
            extra["wikilink_count"] = len(links)

        if not body.strip():
            return []
        return [ExtractedDocument(text=body.strip(), extra_metadata=extra)]
