"""Tests for markdown conversion."""

import pytest

from simplymarkdown.markdown_converter import convert_to_html


class TestConvertToHtml:
    """Tests for convert_to_html function."""

    def test_basic_markdown(self) -> None:
        content = "# Hello World\n\nThis is a paragraph."
        html, meta = convert_to_html(content)
        
        assert "Hello World</h1>" in html
        assert "<p>This is a paragraph.</p>" in html

    def test_bold_and_italic(self) -> None:
        content = "**bold** and *italic*"
        html, meta = convert_to_html(content)
        
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html

    def test_links(self) -> None:
        content = "[Link text](https://example.com)"
        html, meta = convert_to_html(content)
        
        assert 'href="https://example.com"' in html
        assert "Link text" in html

    def test_code_block(self) -> None:
        content = "```python\nprint('hello')\n```"
        html, meta = convert_to_html(content)
        
        assert "print" in html
        assert "hello" in html

    def test_inline_code(self) -> None:
        content = "Use `code` inline"
        html, meta = convert_to_html(content)
        
        assert "<code>code</code>" in html

    def test_frontmatter_extraction(self) -> None:
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

    def test_table(self) -> None:
        content = """
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
"""
        html, meta = convert_to_html(content)
        
        assert "<table>" in html
        assert "<th>" in html or "Header 1" in html

    def test_list_unordered(self) -> None:
        content = """
- Item 1
- Item 2
- Item 3
"""
        html, meta = convert_to_html(content)
        
        assert "<ul>" in html
        assert "<li>" in html

    def test_list_ordered(self) -> None:
        content = """
1. First
2. Second
3. Third
"""
        html, meta = convert_to_html(content)
        
        assert "<ol>" in html
        assert "<li>" in html

    def test_blockquote(self) -> None:
        content = "> This is a quote"
        html, meta = convert_to_html(content)
        
        assert "<blockquote>" in html

    def test_horizontal_rule(self) -> None:
        content = "Before\n\n---\n\nAfter"
        html, meta = convert_to_html(content)
        
        assert "<hr" in html

    def test_image(self) -> None:
        content = "![Alt text](image.png)"
        html, meta = convert_to_html(content)
        
        assert "<img" in html
        assert 'alt="Alt text"' in html

    def test_empty_content(self) -> None:
        html, meta = convert_to_html("")
        assert html == ""
        assert meta == {}
