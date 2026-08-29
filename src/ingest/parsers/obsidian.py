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
_FRONTMATTER_FIELDS = frozenset(
    {
        "title",
        "tags",
        "date",
        "aliases",
        "type",
        "status",
        "priority",
        "area",
        "source",
        "updated",
    }
)


def _frontmatter_metadata(frontmatter: str) -> dict[str, str]:
    """Extract the scalar/list fields used by Obsidian and NextEleven HQ.

    Values are stored as strings because Chroma metadata must remain scalar.
    Simple YAML lists are flattened to comma-separated values; malformed or
    nested YAML is intentionally ignored rather than guessed.
    """
    out: dict[str, str] = {}
    active_list_key: str | None = None
    list_values: list[str] = []

    def flush_list() -> None:
        nonlocal active_list_key, list_values
        if active_list_key and list_values:
            out[f"fm_{active_list_key}"] = ",".join(list_values)[:500]
        active_list_key = None
        list_values = []

    for raw_line in frontmatter.splitlines():
        stripped = raw_line.strip()
        if active_list_key and stripped.startswith("-"):
            value = stripped[1:].strip().strip('"').strip("'")
            if value:
                list_values.append(value)
            continue

        flush_list()
        if not stripped or stripped.startswith("#") or ":" not in raw_line:
            continue
        key, _, value = raw_line.partition(":")
        key = key.strip().lower()
        if key not in _FRONTMATTER_FIELDS:
            continue
        value = value.strip()
        if not value:
            active_list_key = key
            continue
        value = value.strip('"').strip("'")
        if key in {"tags", "aliases"} and value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip('"').strip("'") for item in value[1:-1].split(",")]
            value = ",".join(item for item in items if item)
        if value:
            out[f"fm_{key}"] = value[:500]

    flush_list()
    return out


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
            body = raw[match.end() :]
            extra.update(_frontmatter_metadata(match.group(1)))

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
