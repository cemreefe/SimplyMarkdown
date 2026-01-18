"""Tests for sitemap, RSS, and search index generators."""

import json
import tempfile
from pathlib import Path

import pytest

from simplymarkdown.generators import (
    generate_rss_feed,
    generate_search_index,
    generate_sitemap,
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


def test_sitemap_generation(sample_html_dir: Path) -> None:
    """Test that sitemap is generated with correct content."""
    generate_sitemap(sample_html_dir, "https://example.com")

    sitemap_path = sample_html_dir / "sitemap.xml"
    assert sitemap_path.exists()

    sitemap_content = sitemap_path.read_text()
    assert "<urlset" in sitemap_content
    assert "<url>" in sitemap_content
    assert "<loc>" in sitemap_content
    assert "https://example.com" in sitemap_content


@pytest.mark.parametrize(
    "feed_title,feed_description",
    [
        ("My Blog", "A test blog"),
        (None, None),
    ],
)
def test_rss_generation(sample_html_dir: Path, feed_title: str | None, feed_description: str | None) -> None:
    """Test that RSS feed is generated correctly."""
    kwargs = {}
    if feed_title:
        kwargs["feed_title"] = feed_title
    if feed_description:
        kwargs["feed_description"] = feed_description

    generate_rss_feed(sample_html_dir, "https://example.com", **kwargs)

    rss_path = sample_html_dir / "rss.xml"
    assert rss_path.exists()

    rss_content = rss_path.read_text()
    assert "<channel>" in rss_content
    assert "<item>" in rss_content

    if feed_title:
        assert f"<title>{feed_title}</title>" in rss_content


def test_rss_whitelist(sample_html_dir: Path) -> None:
    """Test that RSS feed respects whitelist patterns."""
    generate_rss_feed(
        sample_html_dir,
        "https://example.com",
        uri_whitelist="posts/*",
    )

    rss_content = (sample_html_dir / "rss.xml").read_text()
    # Should only include posts
    assert "my-post" in rss_content.lower()


def test_search_index_generation(sample_html_dir: Path) -> None:
    """Test that search index is generated with correct structure."""
    generate_search_index(sample_html_dir, "https://example.com")

    index_path = sample_html_dir / "search-index.json"
    assert index_path.exists()

    index_content = index_path.read_text()
    data = json.loads(index_content)

    assert "version" in data
    assert "documents" in data
    assert isinstance(data["documents"], list)
    assert len(data["documents"]) == 2

    # Check document structure
    for doc in data["documents"]:
        assert "id" in doc
        assert "url" in doc
        assert "title" in doc
        assert "content" in doc
