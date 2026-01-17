"""Sitemap generator for SimplyMarkdown."""

from __future__ import annotations

import os
from pathlib import Path

from bs4 import BeautifulSoup


def generate_sitemap(root_directory: str | Path, url_root: str = "") -> None:
    """Generate a sitemap.xml file from rendered HTML files.

    Args:
        root_directory: Root directory containing HTML files.
        url_root: Root URL for the sitemap links.
    """
    root_directory = Path(root_directory)
    html_files = _get_html_files(root_directory)

    output_file = root_directory / "sitemap.xml"

    with open(output_file, "w", encoding="utf-8") as sitemap_file:
        sitemap_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        sitemap_file.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        for file_path in html_files:
            canonical_url = _get_canonical_url(file_path)

            if canonical_url:
                if not canonical_url.startswith(url_root):
                    url = (url_root + canonical_url).replace("//", "/")
                    url = url.replace("https:/", "https://")
                else:
                    url = canonical_url
            else:
                relative_path = file_path.relative_to(root_directory)
                url = f"{url_root}/{relative_path}".replace("\\", "/")
                url = url.replace("//", "/")
                url = url.replace("https:/", "https://")
                url = url.replace(".html", "")

            sitemap_file.write("  <url>\n")
            sitemap_file.write(f"    <loc>{url}</loc>\n")
            sitemap_file.write("  </url>\n")

        sitemap_file.write("</urlset>\n")


def _get_html_files(directory: Path) -> list[Path]:
    """Get all HTML files in a directory recursively."""
    html_files: list[Path] = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".html"):
                html_files.append(Path(root) / file)
    return html_files


def _get_canonical_url(file_path: Path) -> str | None:
    """Extract canonical URL from an HTML file."""
    try:
        with open(file_path, encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")
            canonical_link = soup.find("link", rel="canonical")
            if canonical_link and canonical_link.has_attr("href"):
                return canonical_link["href"]
    except Exception:
        pass
    return None
