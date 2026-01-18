"""Tests for the preview extension."""

import tempfile
from pathlib import Path

import pytest

from simplymarkdown.markdown_converter import convert_to_html


class TestPreviewExtension:
    """Tests for the preview extension functionality."""

    def test_simple_preview(self) -> None:
        """Test that % posts tag renders posts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            posts_dir = tmpdir / "posts"
            posts_dir.mkdir()

            # Create a test post
            post_file = posts_dir / "test-post.md"
            post_file.write_text(
                """---
title: Test Post
date: 2024-01-15
emoji: 🎉
---

# Test Post

This is test content.
"""
            )

            # Create markdown with preview tag
            content = "% posts"
            html, _ = convert_to_html(content, base_path=str(tmpdir))

            assert "postsListWrapper" in html
            assert "Test Post" in html
            assert "🎉" in html

    def test_detailed_preview(self) -> None:
        """Test that % posts:detailed renders detailed previews."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            posts_dir = tmpdir / "posts"
            posts_dir.mkdir()

            # Create a test post
            post_file = posts_dir / "test-post.md"
            post_file.write_text(
                """---
title: Test Post
date: 2024-01-15
---

# Test Post

This is test content.
"""
            )

            # Create markdown with detailed preview tag
            content = "% posts:detailed"
            html, _ = convert_to_html(content, base_path=str(tmpdir))

            assert "postsListWrapper" in html
            assert "postPreview" in html
            assert "Test Post" in html
            assert "test content" in html

    def test_preview_with_relative_image_link(self) -> None:
        """Test that preview handles relative image links correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            posts_dir = tmpdir / "posts"
            posts_dir.mkdir()

            # Create a test post with relative image
            post_file = posts_dir / "test-post.md"
            post_file.write_text(
                """---
title: Test Post
date: 2024-01-15
---

# Test Post

![](./image.jpeg)

Content here.
"""
            )

            # Create markdown with preview tag
            content = "% posts:detailed"
            html, _ = convert_to_html(content, base_path=str(tmpdir))

            # Should not crash and should render the post
            assert "postsListWrapper" in html
            assert "Test Post" in html
            assert "postPreview" in html

    def test_preview_skips_drafts(self) -> None:
        """Test that preview skips draft posts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            posts_dir = tmpdir / "posts"
            posts_dir.mkdir()

            # Create a draft post
            draft_file = posts_dir / "_draft-post.md"
            draft_file.write_text(
                """---
title: Draft Post
---

# Draft Post
"""
            )

            # Create a published post
            post_file = posts_dir / "published-post.md"
            post_file.write_text(
                """---
title: Published Post
date: 2024-01-15
---

# Published Post
"""
            )

            content = "% posts"
            html, _ = convert_to_html(content, base_path=str(tmpdir))

            assert "Published Post" in html
            assert "Draft Post" not in html

    def test_preview_with_nested_directories(self) -> None:
        """Test that preview works with nested post directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            posts_dir = tmpdir / "posts" / "2024" / "01" / "15"
            posts_dir.mkdir(parents=True)

            # Create a test post in nested directory
            post_file = posts_dir / "test-post.md"
            post_file.write_text(
                """---
title: Nested Post
date: 2024-01-15
---

# Nested Post

Content.
"""
            )

            content = "% posts"
            html, _ = convert_to_html(content, base_path=str(tmpdir))

            assert "Nested Post" in html
            assert "postsListWrapper" in html
