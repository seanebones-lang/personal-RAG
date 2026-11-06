"""Tests for the HTML main-content parser (Backlog Wave 8)."""

from pathlib import Path

import pytest

from src.ingest.parsers.html_parser import HtmlMainContentParser
from src.ingest.parsers.registry import extract_documents


@pytest.fixture
def html_path():
    return Path(__file__).parent / "fixtures" / "sample.html"


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_article_page_extracts_main_content_only(html_path):
    docs = HtmlMainContentParser().extract(html_path)

    assert len(docs) == 1
    doc = docs[0]
    assert "The autumn watch begins when the swallows leave" in doc.text
    assert "one hundred and twelve of them" in doc.text
    assert doc.extra_metadata["format"] == "html"
    assert doc.extra_metadata["main_element"] == "article"


def test_boilerplate_and_noncontent_never_reach_the_document(html_path):
    text = HtmlMainContentParser().extract(html_path)[0].text

    assert "Spring" not in text.split("Title:")[1]  # nav links
    assert "All rights reserved" not in text  # footer
    assert "script-only-marker" not in text  # <script> body
    assert "css-only-marker" not in text  # <style> body
    assert "harbour board" not in text  # <aside>


def test_title_line_and_metadata(html_path):
    doc = HtmlMainContentParser().extract(html_path)[0]

    assert doc.text.startswith("Title: The Lantern Keeper's Almanac")
    assert doc.extra_metadata["title"].startswith("The Lantern Keeper's Almanac")


def test_article_header_kept_page_header_dropped(html_path):
    text = HtmlMainContentParser().extract(html_path)[0].text

    # The <h1> lives in a <header> inside the <article>: headline, kept.
    assert "Keeping the Light: Autumn Notes" in text
    assert "By Marta Ellison" in text
    # The <header> directly under <body> is the site banner: dropped.
    assert "About the Press" not in text


def test_list_and_table_blocks_render_as_text(html_path):
    text = HtmlMainContentParser().extract(html_path)[0].text

    assert "Lamp oil, two casks, winter grade" in text
    assert "October | 17:40" in text
    assert "A light kept honestly is a promise" in text


def test_main_element_preferred_over_fatter_div(tmp_path):
    filler = "The tide tables for the lower harbour are pinned beside the door. " * 6
    page = (
        "<html><head><title>Notices</title></head><body>"
        f"<div><p>{filler}</p></div>"
        "<main><p>The ferry to the north island stops running on the last "
        "Friday of October, and the winter timetable, with its single morning "
        "crossing, begins the following Monday for residents and freight, "
        "with tickets sold at the harbour office until the bell rings.</p>"
        "</main></body></html>"
    )
    docs = HtmlMainContentParser().extract(_write(tmp_path, "m.html", page))

    assert len(docs) == 1
    assert docs[0].extra_metadata["main_element"] == "main"
    assert "winter timetable" in docs[0].text
    assert "tide tables" not in docs[0].text


def test_density_fallback_picks_prose_div_over_link_list(tmp_path):
    prose = (
        "The reading room keeps its winter hours from the first of November, "
        "opening at nine and closing when the light fails, and the ledger of "
        "borrowed charts is signed at the desk by the stove each evening."
    )
    page = (
        "<html><head><title>Reading Room</title></head><body>"
        '<div class="links"><a href="/a">Charts</a> <a href="/b">Tides</a> '
        '<a href="/c">Signals</a> <a href="/d">Logs</a></div>'
        f"<div><p>{prose}</p></div>"
        "</body></html>"
    )
    docs = HtmlMainContentParser().extract(_write(tmp_path, "d.html", page))

    assert len(docs) == 1
    assert "reading room keeps its winter hours" in docs[0].text
    assert "Signals" not in docs[0].text


def test_script_and_style_only_page_declines(tmp_path):
    page = (
        "<html><head><title>Redirect</title>"
        "<style>body { margin: 0; }</style>"
        "<script>window.location = '/home'; bootAnalytics();</script>"
        "</head><body><script>renderApp('root');</script></body></html>"
    )
    assert HtmlMainContentParser().extract(_write(tmp_path, "s.html", page)) == []


def test_short_page_declines_to_fallback(tmp_path):
    page = "<html><body><p>Back soon.</p></body></html>"
    assert HtmlMainContentParser().extract(_write(tmp_path, "t.html", page)) == []


def test_empty_and_bodyless_files_decline(tmp_path):
    assert HtmlMainContentParser().extract(_write(tmp_path, "e.html", "")) == []
    page = "<html><head><title>Nothing here</title></head></html>"
    assert HtmlMainContentParser().extract(_write(tmp_path, "n.html", page)) == []


def test_malformed_html_still_extracts(tmp_path):
    page = (
        "<html><body><article><h1>Harbour Notes</h2>"
        "<p>The coaling steamer waits for the morning tide beyond the bar, "
        "and the pilot boat goes out at first light with the mail sacks and "
        "a crate of oranges for the lighthouse families on the outer rock, "
        "as it has every calm morning since before the new pier was built."
        "</article></body>"  # unclosed <p>, mismatched </h2>, file just ends
    )
    docs = HtmlMainContentParser().extract(_write(tmp_path, "bad.html", page))

    assert len(docs) == 1
    assert "Harbour Notes" in docs[0].text
    assert "coaling steamer" in docs[0].text


def test_registry_routes_generic_html_through_the_parser(html_path):
    docs = extract_documents(html_path, fallback_text="<html>raw fallback</html>")

    assert len(docs) == 1
    assert docs[0].extra_metadata["format"] == "html"
    assert "autumn watch begins" in docs[0].text


def test_registry_still_routes_bookmark_exports_to_bookmarks(tmp_path):
    page = (
        "<!DOCTYPE NETSCAPE-Bookmark-file-1><HTML><HEAD>"
        "<TITLE>Bookmarks</TITLE></HEAD><BODY>"
        "<H1>Bookmarks Menu</H1><DL><p>"
        '<DT><A HREF="https://example.invalid/charts" ADD_DATE="1700000000">'
        "Harbour Charts</A>"
        "</DL><p></BODY></HTML>"
    )
    docs = extract_documents(_write(tmp_path, "bookmarks.html", page), fallback_text="ignored")

    assert len(docs) == 1
    assert docs[0].extra_metadata["format"] == "browser_bookmark"
    assert "Harbour Charts" in docs[0].text
