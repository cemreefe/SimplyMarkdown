"""Preview extension for listing posts in a directory."""


import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension


@dataclass
class ContentItem:
    """Represents a content item for preview listings."""

    content: str
    date: str
    href: str
    emoji: str
    tags: list[str]
    title: str
    truncated: bool


def get_first_title(markdown_or_html_text: str) -> str:
    """Extract the first title from markdown or HTML text."""
    pattern = r"(<h[1-6].*?>.+?</h[1-6]>)|#+(\s+(.*?))$"
    match = re.search(pattern, markdown_or_html_text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r"<[^>]+>", "", match.group(0)).strip()
        title = re.sub(r"#+ +", "", title)
        return title
    return ""


def extract_first_paragraph(html: str, character_limit: int = 160) -> str:
    """Extract the first paragraph from HTML content."""
    p_tags = re.findall(r"<p>(.*?)</p>", html, re.DOTALL)

    text_content = ""
    for p_content in p_tags:
        paragraph_text = re.sub(r"<parsers-ignore>.*?</parsers-ignore>", "", p_content)
        paragraph_text = re.sub(r"<.*?>", "", paragraph_text)
        paragraph_text = paragraph_text.strip()

        text_content += paragraph_text
        if len(text_content) >= character_limit:
            return text_content[: character_limit - 5] + "..."

    return text_content


class PreviewExtension(Extension):
    """Markdown extension to handle the special tag for previews.

    Usage in markdown:
        % <directory>           - List all posts in directory
        % <directory>:detailed  - Show detailed previews with content
        % <directory>:paginate:10 - Paginate with 10 items per page
    """

    def __init__(
        self,
        base_path: str | None = None,
        processor: Callable[[str, str], tuple[str, dict]] | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.config = {"preview_limit": [6, "The number of components to show in the preview"]}
        self.base_path = base_path
        self.processor = processor

    def extendMarkdown(self, md: Any) -> None:
        """Register the preview block processor."""
        preview_block = PreviewBlockProcessor(
            self.getConfigs(), md.parser, self.base_path, self.processor
        )
        preview_block.md = md
        md.parser.blockprocessors.register(preview_block, "preview", 175)


class PreviewBlockProcessor(BlockProcessor):
    """Block processor for handling the special tag for previews."""

    PATTERN = re.compile(r"^%\s*([^>]+)$")

    def __init__(
        self,
        config: dict[str, Any],
        parser: Any,
        base_path: str | None = None,
        processor: Callable[[str, str], tuple[str, dict]] | None = None,
    ):
        super().__init__(parser)
        self.directory_name: str | None = None
        self.preview_limit = int(config["preview_limit"])
        self.base_path = base_path
        self.processor = processor
        self.paginate: int | None = None

    def test(self, parent: ET.Element, block: str) -> bool:  # noqa: ARG002
        """Test if the block matches the preview pattern."""
        return bool(self.PATTERN.match(block))

    def run(self, parent: ET.Element, blocks: list[str]) -> None:
        """Process the preview block."""
        block = blocks.pop(0)
        match = self.PATTERN.match(block)
        if not match:
            return

        self.directory_name = match.group(1).strip()
        content_context = self._get_preview_content()
        detailed = content_context.get("detailed", False)
        content_items: list[ContentItem] = content_context.get("content_items", [])
        content_items = sorted(content_items, key=lambda x: x.date, reverse=True)

        # Handle pagination
        paginate = content_context.get("paginate")
        if paginate:
            content_items = content_items[:paginate]

        wrapper = ET.Element("div", attrib={"class": "postsListWrapper"})

        if detailed:
            self._render_detailed(wrapper, content_items)
        else:
            self._render_simple(wrapper, content_items)

        parent.append(wrapper)

    def _render_detailed(self, wrapper: ET.Element, content_items: list[ContentItem]) -> None:
        """Render detailed post previews."""
        for item in content_items:
            date_div = ET.Element("div", attrib={"class": "previewDate"})
            date_div.text = item.date

            text_div = ET.Element("div")
            text_div.text = item.content

            a = ET.Element("a", attrib={"href": item.href, "class": "previewHref"})
            a.append(text_div)

            if item.truncated:
                read_more = ET.Element("span", attrib={"class": "a"})
                read_more.text = "(Read more)"
                a.append(read_more)

            post_wrapper = ET.Element("div", attrib={"class": "postPreview"})
            post_wrapper.append(date_div)
            post_wrapper.append(a)

            wrapper.append(post_wrapper)

    def _render_simple(self, wrapper: ET.Element, content_items: list[ContentItem]) -> None:
        """Render simple post listings grouped by year."""
        prev_yr: str | None = None
        for item in content_items:
            yr = str(item.date.split("-")[0]) if item.date else None

            post_wrapper = ET.Element("div", attrib={"class": "postTitle"})

            if yr != prev_yr:
                date_div = ET.Element("div", attrib={"class": "dateTab"})
                date_div.text = yr
                wrapper.append(date_div)
                prev_yr = yr

            title_div = ET.Element("div")
            title_div.text = f"{item.emoji} {item.title}"

            a = ET.Element("a", attrib={"href": item.href})
            a.append(title_div)

            post_wrapper.append(a)
            wrapper.append(post_wrapper)

    def _get_preview_content(self) -> dict[str, Any]:
        """Get preview content from the specified directory."""
        if not self.directory_name:
            return {}

        # Parse options
        detailed = ":detailed" in self.directory_name
        paginate: int | None = None

        # Check for pagination
        paginate_match = re.search(r":paginate:(\d+)", self.directory_name)
        if paginate_match:
            paginate = int(paginate_match.group(1))

        # Clean directory name
        self.directory_name = re.sub(r":detailed|:paginate:\d+", "", self.directory_name)

        directory_path = (
            os.path.join(self.base_path, self.directory_name)
            if self.base_path
            else self.directory_name
        )

        content_items: list[ContentItem] = []

        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            for root, _, files in sorted(os.walk(directory_path)):
                files.sort()
                relpath = os.path.relpath(root, directory_path)
                for file in files:
                    if not file.lower().endswith(".md"):
                        continue

                    # Skip drafts (files starting with _)
                    if file.startswith("_"):
                        continue

                    item = self._process_file(root, file, relpath)
                    if item:
                        content_items.append(item)

        return {
            "content_items": list(reversed(content_items)),
            "detailed": detailed,
            "paginate": paginate,
        }

    def _process_file(self, root: str, file: str, relpath: str) -> ContentItem | None:
        """Process a single markdown file for preview."""
        href = f"{self.directory_name}/{relpath}/{os.path.splitext(file)[0].replace(', ', '-').replace(' ', '-')}"
        href += os.path.splitext(file)[1] if os.path.splitext(file)[1] != ".md" else ".html"
        href = href.replace(".html", "")

        file_path = os.path.join(root, file)
        try:
            with open(file_path, encoding="utf-8") as md_file:
                file_last_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(
                    "%Y-%m-%d"
                )
                content = md_file.read().strip()

                # Check if draft in frontmatter
                if re.search(r"^draft:\s*true", content, re.MULTILINE | re.IGNORECASE):
                    return None

                content = content.replace("[TOC]", "")
                components = content.split("\n\n")
                components = [c for c in components if "<parsers-ignore>" not in c]
                truncated = self.preview_limit < len(components)
                components = components[: self.preview_limit]
                content = "\n\n".join(components) + "\n\n"

                # Remove tags, includes, and recursive path calls
                content = re.sub(r"\n@ [^\n]*", "", content, flags=re.MULTILINE)
                content = re.sub(r"\n! [^\n]*", "", content, flags=re.MULTILINE)
                content = re.sub(r"\n% [^\n]*", "", content, flags=re.MULTILINE)

                # Fix relative links
                content = re.sub(
                    r"(\[.*?\]\()\.\)",
                    rf"\1 {self.directory_name}/{relpath}/.",
                    content,
                )

                if self.processor:
                    content, meta = self.processor(content, "")
                else:
                    meta = {}

                # Clean up HTML
                content = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", content)
                content = re.sub(r"<h[2-4]\b[^>]*>(.*?)</h[2-4]>", r"<b>\1</b>", content)
                content = re.sub(
                    r"<h1\b[^>]*>(.*?)</h1>",
                    r'<div class="preview-title"><h2>\1</h2></div>',
                    content,
                )

                emoji = meta.get("emoji", ["⏩"])[0]
                date = meta.get("date", [file_last_modified])[0]
                tags = meta.get("tags", [""])
                title = get_first_title(content) or extract_first_paragraph(content)

                return ContentItem(
                    content=content,
                    date=date,
                    href=href,
                    emoji=emoji,
                    tags=tags,
                    title=title,
                    truncated=truncated,
                )
        except Exception as e:
            # Log error for debugging but don't crash
            import sys
            print(f"Warning: Failed to process {file_path}: {e}", file=sys.stderr)
            return None
