"""Markdown to HTML conversion with extensions."""

from __future__ import annotations

from typing import Any

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension

from simplymarkdown.config import CODEHILITE_OPTIONS
from simplymarkdown.extensions.preview import PreviewExtension
from simplymarkdown.extensions.related_posts import RelatedPostsExtension
from simplymarkdown.extensions.toc_module import TocModuleExtension


def setup_codehilite() -> CodeHiliteExtension:
    """Create a configured CodeHilite extension for syntax highlighting."""
    return CodeHiliteExtension(**CODEHILITE_OPTIONS)


def convert_to_html(
    content: str,
    base_path: str = "",
    posts_dir: str | None = None,
    current_file: str | None = None,
) -> tuple[str, dict[str, list[str]]]:
    """Convert markdown content to HTML.

    Args:
        content: Raw markdown string.
        base_path: Base path for resolving relative links.
        posts_dir: Directory containing posts (for related posts feature).
        current_file: Path to current file (for related posts feature).

    Returns:
        Tuple of (html_content, metadata_dict).
    """
    extensions: list[Any] = [
        "markdown.extensions.extra",
        "markdown.extensions.tables",
        "markdown.extensions.fenced_code",
        "markdown.extensions.toc",
        "meta",
        PreviewExtension(
            base_path=base_path,
            processor=lambda c, p: convert_to_html(c, p),
        ),
        TocModuleExtension(),
        setup_codehilite(),
    ]

    # Add related posts extension if posts_dir is provided
    if posts_dir:
        extensions.append(
            RelatedPostsExtension(
                posts_dir=posts_dir,
                current_file=current_file,
            )
        )

    md = markdown.Markdown(extensions=extensions)
    html = md.convert(content)
    meta: dict[str, list[str]] = getattr(md, "Meta", {})

    return html, meta
