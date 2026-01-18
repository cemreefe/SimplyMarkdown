"""Generators for sitemap, RSS, and search index."""

from simplymarkdown.generators.rss import generate_rss_feed
from simplymarkdown.generators.search import generate_search_index
from simplymarkdown.generators.sitemap import generate_sitemap

__all__ = ["generate_sitemap", "generate_rss_feed", "generate_search_index"]
