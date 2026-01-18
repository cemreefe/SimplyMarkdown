"""Tests for markdown conversion."""

import pytest

from simplymarkdown.markdown_converter import convert_to_html


@pytest.mark.parametrize(
    "content,expected_in_html",
    [
        ("# Hello World\n\nThis is a paragraph.", ["Hello World</h1>", "<p>This is a paragraph.</p>"]),
        ("**bold** and *italic*", ["<strong>bold</strong>", "<em>italic</em>"]),
        ("[Link text](https://example.com)", ['href="https://example.com"', "Link text"]),
        ("```python\nprint('hello')\n```", ["print", "hello"]),
        ("Use `code` inline", ["<code>code</code>"]),
        ("| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |", ["<table>", "<th>", "Header 1"]),
        ("- Item 1\n- Item 2\n- Item 3", ["<ul>", "<li>"]),
        ("1. First\n2. Second\n3. Third", ["<ol>", "<li>"]),
        ("> This is a quote", ["<blockquote>"]),
        ("Before\n\n---\n\nAfter", ["<hr"]),
        ("![Alt text](image.png)", ["<img", 'alt="Alt text"']),
    ],
)
def test_markdown_features(content: str, expected_in_html: list[str]) -> None:
    """Test various markdown features convert correctly."""
    html, meta = convert_to_html(content)
    for expected in expected_in_html:
        assert expected in html


def test_frontmatter_extraction() -> None:
    """Test that frontmatter is extracted correctly."""
    content = """---
title: My Title
date: 2024-01-15
tags: test
      example
---

# Content
"""
    html, meta = convert_to_html(content)

    assert meta.get("title") == ["My Title"]
    assert meta.get("date") == ["2024-01-15"]
    assert "test" in meta.get("tags", [])


def test_empty_content() -> None:
    """Test that empty content returns empty results."""
    html, meta = convert_to_html("")
    assert html == ""
    assert meta == {}
