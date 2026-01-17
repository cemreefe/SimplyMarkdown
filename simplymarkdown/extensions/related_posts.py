"""Related posts extension for SimplyMarkdown."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor


@dataclass
class PostInfo:
    """Information about a post for related posts matching."""

    title: str
    href: str
    tags: list[str]
    date: str


class RelatedPostsExtension(Extension):
    """Markdown extension to show related posts based on tags.

    This extension is configured per-file via frontmatter:
        ---
        tags: python, web
        show_related: true
        related_count: 5
        ---
    """

    def __init__(
        self,
        posts_dir: str | None = None,
        current_file: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.posts_dir = posts_dir
        self.current_file = current_file
        self.config = {"max_related": [5, "Maximum number of related posts to show"]}

    def extendMarkdown(self, md: Any) -> None:
        """Register the related posts postprocessor."""
        processor = RelatedPostsPostprocessor(
            md, self.posts_dir, self.current_file, self.getConfigs()
        )
        md.postprocessors.register(processor, "related_posts", 25)


class RelatedPostsPostprocessor(Postprocessor):
    """Postprocessor to add related posts section."""

    def __init__(
        self,
        md: Any,
        posts_dir: str | None,
        current_file: str | None,
        config: dict[str, Any],
    ):
        super().__init__(md)
        self.posts_dir = posts_dir
        self.current_file = current_file
        self.max_related = int(config["max_related"])

    def run(self, text: str) -> str:
        """Add related posts section if enabled in frontmatter."""
        if not hasattr(self.md, "Meta"):
            return text

        meta = self.md.Meta
        show_related = meta.get("show_related", ["false"])[0].lower() == "true"

        if not show_related or not self.posts_dir:
            return text

        current_tags = {tag.strip().lower() for tag in meta.get("tags", [])}
        if not current_tags:
            return text

        related_count = int(meta.get("related_count", [str(self.max_related)])[0])
        related_posts = self._find_related_posts(current_tags, related_count)

        if not related_posts:
            return text

        # Generate related posts HTML
        related_html = self._generate_related_html(related_posts)
        return text + related_html

    def _find_related_posts(self, current_tags: set[str], max_count: int) -> list[PostInfo]:
        """Find posts related by tags."""
        if not self.posts_dir or not os.path.exists(self.posts_dir):
            return []

        scored_posts: list[tuple[int, PostInfo]] = []

        for root, _, files in os.walk(self.posts_dir):
            for file in files:
                if not file.lower().endswith(".md"):
                    continue

                file_path = os.path.join(root, file)

                # Skip current file
                if self.current_file and os.path.samefile(file_path, self.current_file):
                    continue

                # Skip drafts
                if file.startswith("_"):
                    continue

                post_info = self._parse_post(file_path, root)
                if not post_info:
                    continue

                post_tags = {tag.strip().lower() for tag in post_info.tags}
                overlap = len(current_tags & post_tags)

                if overlap > 0:
                    scored_posts.append((overlap, post_info))

        # Sort by overlap score (descending), then by date (descending)
        scored_posts.sort(key=lambda x: (x[0], x[1].date), reverse=True)

        return [post for _, post in scored_posts[:max_count]]

    def _parse_post(self, file_path: str, root: str) -> PostInfo | None:  # noqa: ARG002
        """Parse a post file to extract info."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check if draft
            if re.search(r"^draft:\s*true", content, re.MULTILINE | re.IGNORECASE):
                return None

            # Extract frontmatter
            title = ""
            tags: list[str] = []
            date = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d")

            # Simple frontmatter parsing
            fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                fm_content = fm_match.group(1)
                for line in fm_content.split("\n"):
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip()
                    elif line.startswith("tags:"):
                        tags_str = line.split(":", 1)[1].strip()
                        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                    elif line.startswith("date:"):
                        date = line.split(":", 1)[1].strip()

            # Extract title from content if not in frontmatter
            if not title:
                title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                if title_match:
                    title = title_match.group(1).strip()

            if not title:
                title = os.path.splitext(os.path.basename(file_path))[0]

            # Generate href
            relpath = os.path.relpath(file_path, self.posts_dir) if self.posts_dir else file_path
            href = os.path.splitext(relpath)[0].replace(", ", "-").replace(" ", "-")

            return PostInfo(title=title, href=href, tags=tags, date=date)
        except Exception:
            return None

    def _generate_related_html(self, posts: list[PostInfo]) -> str:
        """Generate HTML for related posts section."""
        html = '\n<div class="related-posts">\n'
        html += "  <h3>Related Posts</h3>\n"
        html += "  <ul>\n"

        for post in posts:
            html += f'    <li><a href="{post.href}">{post.title}</a></li>\n'

        html += "  </ul>\n"
        html += "</div>\n"

        return html
