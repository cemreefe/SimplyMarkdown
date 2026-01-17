"""Tests for sitemap, RSS, and search index generators."""

import tempfile
from pathlib import Path

import pytest

from simplymarkdown.generators import (
    generate_sitemap,
    generate_rss_feed,
    generate_search_index,
)


@pytest.fixture
def sample_html_dir():
    """Create a temporary directory with sample HTML files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create sample HTML files
        index_html = """<!DOCTYPE html>
<html>
<head>
    <title>Home - My Blog</title>
    <link rel="canonical" href="https://example.com/index" />
    <meta name="pubdate" content="Sat, 01 Jan 2024 00:00:00 +0000" />
</head>
<body>
    <main>
        <h1>Welcome</h1>
        <p>This is the home page.</p>
    </main>
</body>
</html>"""
        
        post_html = """<!DOCTYPE html>
<html>
<head>
    <title>My Post - My Blog</title>
    <link rel="canonical" href="https://example.com/posts/my-post" />
    <meta name="pubdate" content="Mon, 15 Jan 2024 00:00:00 +0000" />
</head>
<body>
    <main>
        <categorytag>tech</categorytag>
        <h1>My Post</h1>
        <p>This is a blog post with some content.</p>
    </main>
</body>
</html>"""
        
        (tmpdir / "index.html").write_text(index_html)
        
        posts_dir = tmpdir / "posts"
        posts_dir.mkdir()
        (posts_dir / "my-post.html").write_text(post_html)
        
        yield tmpdir


class TestGenerateSitemap:
    """Tests for sitemap generation."""

    def test_generates_sitemap_file(self, sample_html_dir: Path) -> None:
        generate_sitemap(sample_html_dir, "https://example.com")
        
        sitemap_path = sample_html_dir / "sitemap.xml"
        assert sitemap_path.exists()

    def test_sitemap_contains_urls(self, sample_html_dir: Path) -> None:
        generate_sitemap(sample_html_dir, "https://example.com")
        
        sitemap_content = (sample_html_dir / "sitemap.xml").read_text()
        assert "<urlset" in sitemap_content
        assert "<url>" in sitemap_content
        assert "<loc>" in sitemap_content

    def test_sitemap_uses_canonical_urls(self, sample_html_dir: Path) -> None:
        generate_sitemap(sample_html_dir, "https://example.com")
        
        sitemap_content = (sample_html_dir / "sitemap.xml").read_text()
        assert "https://example.com" in sitemap_content


class TestGenerateRssFeed:
    """Tests for RSS feed generation."""

    def test_generates_rss_file(self, sample_html_dir: Path) -> None:
        generate_rss_feed(sample_html_dir, "https://example.com")
        
        rss_path = sample_html_dir / "rss.xml"
        assert rss_path.exists()

    def test_rss_contains_channel(self, sample_html_dir: Path) -> None:
        generate_rss_feed(
            sample_html_dir,
            "https://example.com",
            feed_title="My Blog",
            feed_description="A test blog",
        )
        
        rss_content = (sample_html_dir / "rss.xml").read_text()
        assert "<channel>" in rss_content
        assert "<title>My Blog</title>" in rss_content

    def test_rss_contains_items(self, sample_html_dir: Path) -> None:
        generate_rss_feed(sample_html_dir, "https://example.com")
        
        rss_content = (sample_html_dir / "rss.xml").read_text()
        assert "<item>" in rss_content

    def test_rss_whitelist(self, sample_html_dir: Path) -> None:
        generate_rss_feed(
            sample_html_dir,
            "https://example.com",
            uri_whitelist="posts/*",
        )
        
        rss_content = (sample_html_dir / "rss.xml").read_text()
        # Should only include posts
        assert "my-post" in rss_content.lower()


class TestGenerateSearchIndex:
    """Tests for search index generation."""

    def test_generates_search_index_file(self, sample_html_dir: Path) -> None:
        generate_search_index(sample_html_dir, "https://example.com")
        
        index_path = sample_html_dir / "search-index.json"
        assert index_path.exists()

    def test_search_index_is_valid_json(self, sample_html_dir: Path) -> None:
        import json
        
        generate_search_index(sample_html_dir, "https://example.com")
        
        index_content = (sample_html_dir / "search-index.json").read_text()
        data = json.loads(index_content)
        
        assert "version" in data
        assert "documents" in data
        assert isinstance(data["documents"], list)

    def test_search_index_contains_documents(self, sample_html_dir: Path) -> None:
        import json
        
        generate_search_index(sample_html_dir, "https://example.com")
        
        index_content = (sample_html_dir / "search-index.json").read_text()
        data = json.loads(index_content)
        
        assert len(data["documents"]) == 2
        
        # Check document structure
        for doc in data["documents"]:
            assert "id" in doc
            assert "url" in doc
            assert "title" in doc
            assert "content" in doc
