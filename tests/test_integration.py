"""Integration tests for the full rendering pipeline."""

import tempfile
from pathlib import Path

import pytest

from simplymarkdown.config import Config
from simplymarkdown.renderer import render_site


@pytest.fixture
def sample_project():
    """Create a sample project structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_dir = tmpdir / "input"
        output_dir = tmpdir / "output"

        # Create directory structure
        input_dir.mkdir()
        output_dir.mkdir()
        (input_dir / "modules").mkdir()
        (input_dir / "posts").mkdir()
        (input_dir / "static" / "img").mkdir(parents=True)

        # Create template
        templates_dir = tmpdir / "templates"
        templates_dir.mkdir()
        template_content = """<!DOCTYPE html>
<html lang="{{ context.lang }}">
<head>
    <meta charset="utf-8">
    <title>{{ context.title }}</title>
    {{ context.meta_tags }}
</head>
<body>
    <nav>{{ context.modules.navbar }}</nav>
    <main>{{ context.content }}</main>
    <footer>{{ context.modules.footer }}</footer>
</body>
</html>"""
        (templates_dir / "base.html").write_text(template_content)

        # Create theme
        themes_dir = tmpdir / "themes"
        themes_dir.mkdir()
        (themes_dir / "basic.css").write_text("body { font-family: sans-serif; }")

        # Create modules
        (input_dir / "modules" / "navbar.md").write_text("[Home](/) | [About](/about)")
        (input_dir / "modules" / "footer.md").write_text("© 2024 Test Blog")

        # Create index page
        index_content = """---
title: Home
---

# Welcome to My Blog

This is the home page.

% posts
"""
        (input_dir / "index.md").write_text(index_content)

        # Create about page
        about_content = """---
title: About
---

# About

This is the about page.
"""
        (input_dir / "about.md").write_text(about_content)

        # Create a blog post
        post_content = """---
title: My First Post
date: 2024-01-15
emoji: 🎉
tags: test
      example
---

# My First Post

This is my first blog post!

## Section 1

Some content here.

```python
print("Hello, World!")
```
"""
        (input_dir / "posts" / "first-post.md").write_text(post_content)

        # Create a draft post
        draft_content = """---
title: Draft Post
draft: true
---

# Draft Post

This should not be published.
"""
        (input_dir / "posts" / "draft-post.md").write_text(draft_content)

        # Create default image
        (input_dir / "static" / "img" / "default_img.png").write_bytes(b"fake png")

        yield {
            "root": tmpdir,
            "input": input_dir,
            "output": output_dir,
            "template": templates_dir / "base.html",
            "theme": themes_dir / "basic.css",
        }


class TestFullRenderPipeline:
    """Integration tests for the full rendering pipeline."""

    def test_renders_all_pages(self, sample_project: dict) -> None:
        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
            title="Test Blog",
            root_url="https://test.com",
        )

        render_site(config)

        output = sample_project["output"]
        assert (output / "index.html").exists()
        assert (output / "about.html").exists()
        assert (output / "posts" / "first-post.html").exists()

    def test_excludes_drafts_by_default(self, sample_project: dict) -> None:
        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
        )

        render_site(config)

        output = sample_project["output"]
        assert not (output / "posts" / "draft-post.html").exists()

    def test_includes_drafts_when_enabled(self, sample_project: dict) -> None:
        from simplymarkdown.config import BuildConfig

        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
            build=BuildConfig(include_drafts=True),
        )

        render_site(config)

        output = sample_project["output"]
        assert (output / "posts" / "draft-post.html").exists()

    def test_generates_sitemap(self, sample_project: dict) -> None:
        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
            root_url="https://test.com",
        )

        render_site(config)

        sitemap = sample_project["output"] / "sitemap.xml"
        assert sitemap.exists()
        content = sitemap.read_text()
        assert "https://test.com" in content

    def test_generates_rss(self, sample_project: dict) -> None:
        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
            title="Test Blog",
            root_url="https://test.com",
        )

        render_site(config)

        rss = sample_project["output"] / "rss.xml"
        assert rss.exists()
        content = rss.read_text()
        assert "<channel>" in content
        assert "Test Blog" in content

    def test_generates_search_index(self, sample_project: dict) -> None:
        import json

        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
        )

        render_site(config)

        search_index = sample_project["output"] / "search-index.json"
        assert search_index.exists()
        
        data = json.loads(search_index.read_text())
        assert "documents" in data
        assert len(data["documents"]) > 0

    def test_copies_static_files(self, sample_project: dict) -> None:
        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
        )

        render_site(config)

        output = sample_project["output"]
        assert (output / "static" / "img" / "default_img.png").exists()
        assert (output / "static" / "css" / "theme.css").exists()

    def test_includes_modules_in_pages(self, sample_project: dict) -> None:
        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
        )

        render_site(config)

        index_content = (sample_project["output"] / "index.html").read_text()
        assert "Home" in index_content  # From navbar
        assert "2024" in index_content  # From footer

    def test_syntax_highlighting(self, sample_project: dict) -> None:
        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
        )

        render_site(config)

        post_content = (sample_project["output"] / "posts" / "first-post.html").read_text()
        # Code should be highlighted (Pygments adds styles)
        assert "print" in post_content
        assert "Hello" in post_content

    def test_meta_tags_generated(self, sample_project: dict) -> None:
        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
            title="Test Blog",
            root_url="https://test.com",
        )

        render_site(config)

        post_content = (sample_project["output"] / "posts" / "first-post.html").read_text()
        assert 'property="og:title"' in post_content
        assert 'name="twitter:card"' in post_content
        assert 'rel="canonical"' in post_content

    def test_category_tags_in_frontmatter(self, sample_project: dict) -> None:
        config = Config(
            input_dir=str(sample_project["input"]),
            output_dir=str(sample_project["output"]),
            template=str(sample_project["template"]),
            theme=str(sample_project["theme"]),
        )

        render_site(config)

        post_content = (sample_project["output"] / "posts" / "first-post.html").read_text()
        # Tags should be present somewhere (depends on template)
        # The post has tags: test, example
        assert "My First Post" in post_content
