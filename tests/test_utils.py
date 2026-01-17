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


class TestGetFilenameWithoutExtension:
    """Tests for get_filename_without_extension function."""

    def test_simple_filename(self) -> None:
        assert get_filename_without_extension("test.md") == "test"

    def test_path_with_directories(self) -> None:
        assert get_filename_without_extension("/path/to/file.md") == "file"

    def test_multiple_dots(self) -> None:
        assert get_filename_without_extension("my.file.name.md") == "my.file.name"

    def test_no_extension(self) -> None:
        assert get_filename_without_extension("README") == "README"


class TestGetExtension:
    """Tests for get_extension function."""

    def test_simple_extension(self) -> None:
        assert get_extension("test.md") == "md"

    def test_html_extension(self) -> None:
        assert get_extension("page.html") == "html"

    def test_no_extension(self) -> None:
        assert get_extension("README") == ""

    def test_path_with_directories(self) -> None:
        assert get_extension("/path/to/file.css") == "css"


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_spaces_to_dashes(self) -> None:
        assert sanitize_filename("my file name") == "my-file-name"

    def test_commas_to_dashes(self) -> None:
        assert sanitize_filename("hello, world") == "hello-world"

    def test_combined(self) -> None:
        assert sanitize_filename("my file, example") == "my-file-example"

    def test_no_changes_needed(self) -> None:
        assert sanitize_filename("already-clean") == "already-clean"


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


class TestGetFirstTitle:
    """Tests for get_first_title function."""

    def test_markdown_h1(self) -> None:
        text = "# My Title\n\nSome content"
        assert get_first_title(text) == "My Title"

    def test_markdown_h2(self) -> None:
        text = "## Second Level\n\nContent"
        assert get_first_title(text) == "Second Level"

    def test_html_h1(self) -> None:
        text = "<h1>HTML Title</h1>"
        assert get_first_title(text) == "HTML Title"

    def test_html_with_class(self) -> None:
        text = '<h1 class="title">Styled Title</h1>'
        assert get_first_title(text) == "Styled Title"

    def test_no_title(self) -> None:
        text = "Just some plain text without titles."
        assert get_first_title(text) == ""


class TestIsDraft:
    """Tests for is_draft function."""

    def test_underscore_prefix(self) -> None:
        assert is_draft("_draft-post.md") is True
        assert is_draft("/path/to/_draft.md") is True

    def test_normal_file(self) -> None:
        assert is_draft("regular-post.md") is False

    def test_draft_frontmatter(self) -> None:
        meta = {"draft": ["true"]}
        assert is_draft("post.md", meta) is True

    def test_not_draft_frontmatter(self) -> None:
        meta = {"draft": ["false"]}
        assert is_draft("post.md", meta) is False

    def test_no_draft_in_meta(self) -> None:
        meta = {"title": ["My Post"]}
        assert is_draft("post.md", meta) is False
