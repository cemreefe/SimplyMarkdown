"""Utility functions for SimplyMarkdown."""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from simplymarkdown.config import (
    CONVERT_TAG,
    DEFAULT_META_IMAGE,
    EMOJI_SERVICE_URL,
    HTML_EXTENSION,
    MARKDOWN_EXTENSIONS,
)


def read_file_content(file_path: str | Path) -> str:
    """Read and return the content of a file.

    Args:
        file_path: Path to the file to read.

    Returns:
        The file content as a string.
    """
    with open(file_path, encoding="utf-8") as file:
        return file.read()


def get_filename_without_extension(full_path: str | Path) -> str:
    """Get the filename without extension from a full file path.

    Args:
        full_path: Full path to the file.

    Returns:
        The filename without its extension.
    """
    file_name_with_extension = os.path.basename(full_path)
    filename, _ = os.path.splitext(file_name_with_extension)
    return filename


def get_extension(full_path: str | Path) -> str:
    """Get the extension from a full file path (without the leading dot).

    Args:
        full_path: Full path to the file.

    Returns:
        The file extension without the leading dot.
    """
    file_name_with_extension = os.path.basename(full_path)
    _, extension = os.path.splitext(file_name_with_extension)
    return extension.lstrip(".")


def fill_template(context: dict[str, Any], template_path: str | Path) -> str:
    """Fill the HTML template with the given context.

    Args:
        context: Dictionary of context variables for the template.
        template_path: Path to the Jinja2 template file.

    Returns:
        The rendered HTML string.
    """
    template_path = Path(template_path)
    env = Environment(loader=FileSystemLoader(template_path.parent))
    template = env.get_template(template_path.name)
    return template.render(context)


def copy_css_file(css_path: str | Path, output_path: str | Path) -> None:
    """Copy the CSS file to the output directory.

    Args:
        css_path: Path to the source CSS file.
        output_path: Root output directory.
    """
    css_output_dir = Path(output_path) / "static" / "css"
    css_output_dir.mkdir(parents=True, exist_ok=True)
    output_css_path = css_output_dir / "theme.css"
    shutil.copy2(css_path, output_css_path)


def get_emoji_favicon_url(emoji: str) -> str:
    """Get the URL for an emoji favicon.

    Args:
        emoji: The emoji character to use as favicon.

    Returns:
        URL to the emoji PNG image.
    """
    return f"{EMOJI_SERVICE_URL}{emoji}.png"


def should_convert_file(file_path: str | Path) -> bool:
    """Check if a file should be converted to HTML.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if the file should be converted, False otherwise.
    """
    file_path = str(file_path).lower()
    if any(file_path.endswith(ext) for ext in MARKDOWN_EXTENSIONS):
        return True
    if file_path.endswith(HTML_EXTENSION):
        with open(file_path, encoding="utf-8") as f:
            return CONVERT_TAG in f.read()
    return False


def is_draft(file_path: str | Path, meta: dict[str, list[str]] | None = None) -> bool:
    """Check if a file is a draft.

    A file is considered a draft if:
    - Its filename starts with an underscore (_)
    - Its frontmatter contains 'draft: true'

    Args:
        file_path: Path to the file.
        meta: Optional parsed frontmatter metadata.

    Returns:
        True if the file is a draft, False otherwise.
    """
    filename = os.path.basename(file_path)
    if filename.startswith("_"):
        return True
    return bool(meta and meta.get("draft", ["false"])[0].lower() == "true")


def replace_relative_src_links(html_content: str, rel_dir: str, root_url: str) -> str:
    """Replace relative src attributes with absolute URLs.

    Args:
        html_content: HTML content to process.
        rel_dir: Relative directory path.
        root_url: Root URL of the website.

    Returns:
        HTML content with updated src attributes.
    """
    root_url = root_url.rstrip("/")
    rel_dir = rel_dir.lstrip("/").rstrip("/")

    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup.find_all(src=True):
        src = tag["src"]
        if not src.startswith(("http://", "https://", "/")):
            new_src = urljoin(f"{root_url}/{rel_dir}/", src)
            tag["src"] = new_src
        elif src.startswith("/"):
            src = src.lstrip("/")
            new_src = urljoin(root_url + "/", src)
            tag["src"] = new_src

    return str(soup)


def get_meta_tags(
    image: str | None,
    title: str,
    description: str,
    pub_date: str,
    root_url: str,
    current_dir: str,
    input_path: str,
    output_file_relpath: str,
    canonical_uri_override: str | None = None,
) -> str:
    """Generate meta tags for SEO and social sharing.

    Args:
        image: Override image URL for meta tags.
        title: Page title.
        description: Page description.
        pub_date: Publication date (YYYY-MM-DD format).
        root_url: Root URL of the website.
        current_dir: Current directory path.
        input_path: Input directory path.
        output_file_relpath: Relative path to output file.
        canonical_uri_override: Optional override for canonical URL.

    Returns:
        HTML string containing meta tags.
    """
    current_dir_relpath = (
        os.path.relpath(current_dir, input_path) if current_dir and input_path else ""
    )

    canonical_url = os.path.join(root_url, canonical_uri_override or output_file_relpath)
    canonical_url = canonical_url.replace(".html", "")

    if image:
        meta_img = image
        if not meta_img.startswith("http"):
            meta_img = os.path.join(root_url, current_dir_relpath, meta_img)
    else:
        meta_img = root_url + DEFAULT_META_IMAGE

    formatted_pub_date = ""
    if pub_date:
        try:
            formatted_pub_date = datetime.strptime(pub_date, "%Y-%m-%d").strftime(
                "%a, %d %b %Y %H:%M:%S +0000"
            )
        except ValueError:
            formatted_pub_date = pub_date

    meta_tags = f'''
    <meta name="description" content="{description}" />
    <meta property="og:title" name="title" content="{title}" />
    <meta property="og:image" name="image" content="{meta_img}" />
    <meta property="og:description" name="description" content="{description}" />
    <meta property="og:type" content="website" />
    <meta property="og:url" name="url" content="{canonical_url}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{title}" />
    <meta name="twitter:description" content="{description}" />
    <meta name="twitter:image" content="{meta_img}" />
    <link rel="canonical" href="{canonical_url}" />
    <meta property="og:pubdate" name="pubdate" content="{formatted_pub_date}" />
    '''

    return meta_tags


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for use in URLs.

    Args:
        filename: The filename to sanitize.

    Returns:
        Sanitized filename with spaces and commas replaced.
    """
    return filename.replace(", ", "-").replace(" ", "-")


def extract_first_paragraph(html: str, character_limit: int = 160) -> str:
    """Extract the first paragraph from HTML content.

    Args:
        html: HTML content to extract from.
        character_limit: Maximum characters to return.

    Returns:
        The extracted text, truncated if necessary.
    """
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


def get_first_title(markdown_or_html_text: str) -> str:
    """Extract the first title from markdown or HTML text.

    Args:
        markdown_or_html_text: Text to extract title from.

    Returns:
        The extracted title, or empty string if none found.
    """
    pattern = r"(<h[1-6].*?>.+?</h[1-6]>)|#+(\s+(.*?))$"
    match = re.search(pattern, markdown_or_html_text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r"<[^>]+>", "", match.group(0)).strip()
        title = re.sub(r"#+ +", "", title)
        return title
    return ""
