"""Structured HTML (.html/.htm) parser — main content, boilerplate stripped.

Backlog Wave 8 ("HTML main-content + CSV structure parsers"): until now a
non-bookmark .html file fell through the registry to the plain-text
fallback, so a saved page was ingested as its raw markup — tags, <script>
and <style> bodies, navigation, sidebars and footers all chunked as if
they were the page's content. Retrieval over that answers "what does this
page say" poorly, because the page's actual prose may be a small fraction
of the indexed text, diluted by chrome that repeats across every page.

This parser extracts the page's main content and emits one
ExtractedDocument for the page: the <title> rendered as a ``Title:`` line
(the self-describing style the CSV parser uses for rows), then the main
element's block-level text in document order. The pipeline chunks the
result as usual, so blocks stay in reading order and the title travels
with the first chunk.

Main-content selection is structural only — no class/id guessing:
- Subtrees that are chrome by tag are pruned wherever they appear:
  script, style, noscript, template, iframe, svg, nav, footer, aside,
  form, button, select, textarea. A <header> is pruned only at page
  level (a direct child of <body>/<html>); inside an article it usually
  carries the headline and is kept.
- The first substantial <article> wins; else the first substantial
  <main>; else the container (div/section/body) whose block text yield
  is highest. "Substantial" means at least MIN_MAIN_CHARS of block text.
- Link farms are not content: a block or container whose text is at
  least 80% link text and no longer than a sentence or two is skipped,
  which is what keeps div-soup navigation out of the density fallback.

Deliberate limits (this parser declines rather than guesses):
- Less than MIN_MAIN_CHARS of extractable main content -> returns [] so
  the existing plain-text fallback keeps behaviour for splash pages,
  redirect stubs and script-only shells instead of indexing a guess.
- No class/id heuristics: a "sidebar" that is a plain <div> full of
  prose will be treated as prose. Semantic markup is the contract.
- Caps mirror the CSV parser: at most MAX_BLOCKS blocks per page and
  MAX_BLOCK_CHARS per block, so a pathological page cannot flood the
  vault; input is also capped at MAX_INPUT_CHARS for the same reason.
- Bookmark exports never reach this parser: the registry tries
  BookmarksHTMLParser first and it claims them.
"""

from __future__ import annotations

import logging
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Tuple

from src.ingest.parsers.base import BaseParser, ExtractedDocument

logger = logging.getLogger(__name__)

MAX_BLOCKS = 10_000
MAX_BLOCK_CHARS = 2_000
MAX_INPUT_CHARS = 2_000_000
MIN_MAIN_CHARS = 200

_SKIP_SUBTREES = frozenset(
    {
        "script",
        "style",
        "noscript",
        "template",
        "iframe",
        "svg",
        "nav",
        "footer",
        "aside",
        "form",
        "button",
        "select",
        "textarea",
    }
)
_BLOCK_TAGS = frozenset(
    {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
        "pre",
        "figcaption",
        "dt",
        "dd",
        "caption",
    }
)
_CELL_TAGS = frozenset({"td", "th"})
_CANDIDATE_TAGS = frozenset({"article", "main", "section", "div", "body"})
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_LINK_FARM_DENSITY = 0.8
_LINK_FARM_MAX_CHARS = 120


class _Node:
    """Minimal element node: a tag plus ordered children (nodes/strings)."""

    __slots__ = ("tag", "children")

    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.children: List[_Node | str] = []


class _TreeBuilder(HTMLParser):
    """Forgiving HTML -> _Node tree builder (stdlib html.parser).

    Malformed markup nests instead of raising; stray closing tags are
    ignored, so a broken page still yields its readable tree.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root")
        self._stack: List[_Node] = [self.root]

    def handle_starttag(self, tag: str, attrs: list) -> None:
        node = _Node(tag)
        self._stack[-1].children.append(node)
        if tag not in _VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self._stack[-1].children.append(_Node(tag))

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                break

    def handle_data(self, data: str) -> None:
        self._stack[-1].children.append(data)


def _prune(node: _Node, page_level: bool = False) -> None:
    """Remove chrome subtrees in place.

    ``page_level`` is true for <html>/<body> themselves: a <header> that
    is a direct child of either is site chrome, while a <header> nested
    inside content usually carries the article headline and stays.
    """
    kept: List[_Node | str] = []
    for child in node.children:
        if isinstance(child, _Node):
            if child.tag in _SKIP_SUBTREES:
                continue
            if child.tag == "header" and page_level:
                continue
            _prune(child, page_level=child.tag in ("html", "body"))
        kept.append(child)
    node.children = kept


def _text_of(node: _Node) -> str:
    """All descendant text, whitespace-collapsed (link text included)."""
    parts: List[str] = []

    def walk(n: _Node) -> None:
        for child in n.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                walk(child)

    walk(node)
    return " ".join("".join(parts).split())


def _link_text_len(node: _Node) -> int:
    total = 0
    for child in node.children:
        if isinstance(child, _Node):
            if child.tag == "a":
                total += len(_text_of(child))
            else:
                total += _link_text_len(child)
    return total


def _is_link_farm(node: _Node) -> bool:
    """True for short subtrees that are (almost) all link text."""
    text_len = len(_text_of(node))
    if text_len == 0 or text_len > _LINK_FARM_MAX_CHARS:
        return False
    return _link_text_len(node) / text_len >= _LINK_FARM_DENSITY


_INLINE_TAGS = frozenset(
    {
        "a",
        "abbr",
        "b",
        "cite",
        "code",
        "em",
        "i",
        "mark",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
        "time",
        "u",
    }
)


def _blocks_from(node: _Node) -> List[str]:
    """Block-level text of a subtree, in document order.

    Inline elements merge into the surrounding text run; block elements
    and containers flush the run and contribute their own blocks, so a
    sentence split by a <b> stays one block in the right position.
    """
    blocks: List[str] = []
    run: List[str] = []

    def flush() -> None:
        text = " ".join("".join(run).split())
        if text:
            blocks.append(text)
        run.clear()

    for child in node.children:
        if isinstance(child, str):
            run.append(child)
            continue
        if _is_link_farm(child):
            continue
        if child.tag in _INLINE_TAGS:
            run.append(_text_of(child))
        elif child.tag in _BLOCK_TAGS:
            flush()
            text = _raw_text(child) if child.tag == "pre" else _text_of(child)
            if text:
                blocks.append(text)
        elif child.tag == "tr":
            flush()
            cells = [
                _text_of(c) for c in child.children if isinstance(c, _Node) and c.tag in _CELL_TAGS
            ]
            line = " | ".join(c for c in cells if c)
            if line:
                blocks.append(line)
        else:
            flush()
            blocks.extend(_blocks_from(child))
    flush()
    return blocks


def _raw_text(node: _Node) -> str:
    """Descendant text with internal newlines kept (for <pre>)."""
    parts: List[str] = []

    def walk(n: _Node) -> None:
        for child in n.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                walk(child)

    walk(node)
    return "".join(parts).strip()


def _find_all(node: _Node, tag: str) -> List[_Node]:
    found: List[_Node] = []
    for child in node.children:
        if isinstance(child, _Node):
            if child.tag == tag:
                found.append(child)
            found.extend(_find_all(child, tag))
    return found


def _candidates(node: _Node) -> List[_Node]:
    found: List[_Node] = []
    for child in node.children:
        if isinstance(child, _Node):
            if child.tag in _CANDIDATE_TAGS:
                found.append(child)
            found.extend(_candidates(child))
    return found


def _select_main(root: _Node) -> Tuple[Optional[_Node], List[str]]:
    """Pick the main-content element; returns (node, its blocks)."""
    for tag in ("article", "main"):
        best: Optional[_Node] = None
        best_blocks: List[str] = []
        best_len = 0
        for node in _find_all(root, tag):
            blocks = _blocks_from(node)
            total = sum(len(b) for b in blocks)
            if total >= MIN_MAIN_CHARS and total > best_len:
                best, best_blocks, best_len = node, blocks, total
        if best is not None:
            return best, best_blocks
    best = None
    best_blocks = []
    best_len = 0
    for node in _candidates(root):
        blocks = _blocks_from(node)
        total = sum(len(b) for b in blocks)
        if total > best_len:
            best, best_blocks, best_len = node, blocks, total
    if best is not None and best_len >= MIN_MAIN_CHARS:
        return best, best_blocks
    return None, []


class HtmlMainContentParser(BaseParser):
    """Extracts a page's main content as a single self-describing document."""

    extensions = frozenset({".html", ".htm"})

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        try:
            raw = file_path.read_bytes()
        except OSError:
            return []
        text = raw.decode("utf-8", errors="ignore")
        if not text.strip() or len(text) > MAX_INPUT_CHARS:
            return []

        builder = _TreeBuilder()
        try:
            builder.feed(text)
            builder.close()
        except Exception as exc:  # html.parser is forgiving; belt and braces
            logger.warning("HTML parse failed for %s: %s", file_path, exc)
            return []
        root = builder.root
        _prune(root, page_level=True)

        titles = _find_all(root, "title")
        title = _text_of(titles[0]) if titles else ""

        main, blocks = _select_main(root)
        if main is None:
            return []

        lines: List[str] = []
        if title:
            lines.append(f"Title: {title[:MAX_BLOCK_CHARS]}")
        lines.extend(b[:MAX_BLOCK_CHARS] for b in blocks[:MAX_BLOCKS])
        body = "\n\n".join(lines)
        if not body.strip():
            return []

        extra = {"format": "html", "main_element": main.tag}
        if title:
            extra["title"] = title[:500]
        return [ExtractedDocument(text=body, extra_metadata=extra)]
