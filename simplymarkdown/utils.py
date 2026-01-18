"""Utility functions for SimplyMarkdown."""

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
    """Read and return file content."""
    with open(file_path, encoding="utf-8") as file:
        return file.read()


def get_filename_without_extension(full_path: str | Path) -> str:
    """Get filename without extension."""
    return os.path.splitext(os.path.basename(full_path))[0]


def get_extension(full_path: str | Path) -> str:
    """Get file extension without leading dot."""
    _, extension = os.path.splitext(os.path.basename(full_path))
    return extension.lstrip(".")


def fill_template(context: dict[str, Any], template_path: str | Path) -> str:
    """Fill HTML template with context."""
    template_path = Path(template_path)
    env = Environment(loader=FileSystemLoader(template_path.parent))
    return env.get_template(template_path.name).render(context)


def copy_css_file(css_path: str | Path, output_path: str | Path) -> None:
    """Copy CSS file to output directory."""
    css_output_dir = Path(output_path) / "static" / "css"
    css_output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(css_path, css_output_dir / "theme.css")


def get_emoji_favicon_url(emoji: str) -> str:
    """Get URL for emoji favicon."""
    return f"{EMOJI_SERVICE_URL}{emoji}.png"


def should_convert_file(file_path: str | Path) -> bool:
    """Check if file should be converted to HTML."""
    file_path = str(file_path).lower()
    if any(file_path.endswith(ext) for ext in MARKDOWN_EXTENSIONS):
        return True
    if file_path.endswith(HTML_EXTENSION):
        with open(file_path, encoding="utf-8") as f:
            return CONVERT_TAG in f.read()
    return False


def is_draft(file_path: str | Path, meta: dict[str, list[str]] | None = None) -> bool:
    """Check if file is a draft (underscore prefix or draft: true in frontmatter)."""
    if os.path.basename(file_path).startswith("_"):
        return True
    return bool(meta and meta.get("draft", ["false"])[0].lower() == "true")


def replace_relative_src_links(html_content: str, rel_dir: str, root_url: str) -> str:
    """Replace relative src attributes with absolute URLs."""
    root_url = root_url.rstrip("/")
    rel_dir = rel_dir.lstrip("/").rstrip("/")
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup.find_all(src=True):
        src = tag["src"]
        if not src.startswith(("http://", "https://", "/")):
            tag["src"] = urljoin(f"{root_url}/{rel_dir}/", src)
        elif src.startswith("/"):
            tag["src"] = urljoin(root_url + "/", src.lstrip("/"))

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
    """Generate meta tags for SEO and social sharing."""
    current_dir_relpath = os.path.relpath(current_dir, input_path) if current_dir and input_path else ""
    canonical_url = os.path.join(root_url, canonical_uri_override or output_file_relpath).replace(".html", "")

    if image:
        meta_img = image if image.startswith("http") else os.path.join(root_url, current_dir_relpath, image)
    else:
        meta_img = root_url + DEFAULT_META_IMAGE

    formatted_pub_date = ""
    if pub_date:
        try:
            formatted_pub_date = datetime.strptime(pub_date, "%Y-%m-%d").strftime("%a, %d %b %Y %H:%M:%S +0000")
        except ValueError:
            formatted_pub_date = pub_date

    return f'''
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


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for URLs (spaces and commas to dashes)."""
    return filename.replace(", ", "-").replace(" ", "-")


def extract_first_paragraph(html: str, character_limit: int = 160) -> str:
    """Extract first paragraph from HTML, truncated to character_limit."""
    text_content = ""
    for p_content in re.findall(r"<p>(.*?)</p>", html, re.DOTALL):
        paragraph_text = re.sub(r"<parsers-ignore>.*?</parsers-ignore>|<.*?>", "", p_content).strip()
        text_content += paragraph_text
        if len(text_content) >= character_limit:
            return text_content[: character_limit - 5] + "..."
    return text_content


def get_first_title(markdown_or_html_text: str) -> str:
    """Extract first title from markdown or HTML."""
    match = re.search(r"(<h[1-6].*?>.+?</h[1-6]>)|#+(\s+(.*?))$", markdown_or_html_text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r"<[^>]+>|#+ +", "", match.group(0)).strip()
        return title
    return ""
