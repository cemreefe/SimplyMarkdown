"""Tests for utility functions."""

import pytest

from simplymarkdown.utils import (
    get_filename_without_extension,
    get_extension,
    sanitize_filename,
    extract_first_paragraph,
    get_first_title,
    should_convert_file,
    is_draft,
)


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("test.md", "test"),
        ("/path/to/file.md", "file"),
        ("my.file.name.md", "my.file.name"),
        ("README", "README"),
    ],
)
def test_get_filename_without_extension(filename: str, expected: str) -> None:
    assert get_filename_without_extension(filename) == expected


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("test.md", "md"),
        ("page.html", "html"),
        ("README", ""),
        ("/path/to/file.css", "css"),
    ],
)
def test_get_extension(filename: str, expected: str) -> None:
    assert get_extension(filename) == expected


@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("my file name", "my-file-name"),
        ("hello, world", "hello-world"),
        ("my file, example", "my-file-example"),
        ("already-clean", "already-clean"),
    ],
)
def test_sanitize_filename(input_str: str, expected: str) -> None:
    assert sanitize_filename(input_str) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# My Title\n\nSome content", "My Title"),
        ("## Second Level\n\nContent", "Second Level"),
        ("<h1>HTML Title</h1>", "HTML Title"),
        ('<h1 class="title">Styled Title</h1>', "Styled Title"),
        ("Just some plain text without titles.", ""),
    ],
)
def test_get_first_title(text: str, expected: str) -> None:
    assert get_first_title(text) == expected


@pytest.mark.parametrize(
    "filename,meta,expected",
    [
        ("_draft-post.md", None, True),
        ("/path/to/_draft.md", None, True),
        ("regular-post.md", None, False),
        ("post.md", {"draft": ["true"]}, True),
        ("post.md", {"draft": ["false"]}, False),
        ("post.md", {"title": ["My Post"]}, False),
    ],
)
def test_is_draft(filename: str, meta: dict | None, expected: bool) -> None:
    assert is_draft(filename, meta) == expected


class TestExtractFirstParagraph:
    """Tests for extract_first_paragraph function."""

    def test_single_paragraph(self) -> None:
        html = "<p>This is a test paragraph.</p>"
        assert extract_first_paragraph(html) == "This is a test paragraph."

    def test_multiple_paragraphs(self) -> None:
        html = "<p>First paragraph.</p><p>Second paragraph.</p>"
        assert extract_first_paragraph(html) == "First paragraph.Second paragraph."

    def test_truncation(self) -> None:
        html = "<p>" + "a" * 200 + "</p>"
        result = extract_first_paragraph(html, character_limit=50)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_strips_inner_tags(self) -> None:
        html = "<p>Text with <strong>bold</strong> and <em>italic</em>.</p>"
        assert extract_first_paragraph(html) == "Text with bold and italic."

    def test_empty_html(self) -> None:
        assert extract_first_paragraph("") == ""
