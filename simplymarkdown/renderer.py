"""Main rendering engine for SimplyMarkdown."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from simplymarkdown.config import (
    DEFAULT_LANGUAGE,
    MODULES_DIR,
    Config,
)
from simplymarkdown.generators import (
    generate_rss_feed,
    generate_search_index,
    generate_sitemap,
)
from simplymarkdown.markdown_converter import convert_to_html
from simplymarkdown.utils import (
    copy_css_file,
    extract_first_paragraph,
    fill_template,
    get_emoji_favicon_url,
    get_extension,
    get_filename_without_extension,
    get_first_title,
    get_meta_tags,
    is_draft,
    read_file_content,
    replace_relative_src_links,
    should_convert_file,
)


class BuildManifest:
    """Tracks file hashes for incremental builds."""

    def __init__(self, output_path: Path):
        self.manifest_path = output_path / ".simplymarkdown" / "manifest.json"
        self.hashes: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load existing manifest."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path) as f:
                    self.hashes = json.load(f)
            except Exception:
                self.hashes = {}

    def save(self) -> None:
        """Save manifest to disk."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(self.hashes, f, indent=2)

    def get_hash(self, file_path: Path) -> str:
        """Calculate hash of a file."""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def needs_rebuild(self, file_path: Path) -> bool:
        """Check if a file needs to be rebuilt."""
        key = str(file_path)
        current_hash = self.get_hash(file_path)
        stored_hash = self.hashes.get(key)
        return current_hash != stored_hash

    def update(self, file_path: Path) -> None:
        """Update hash for a file."""
        self.hashes[str(file_path)] = self.get_hash(file_path)


class Renderer:
    """Main renderer class for SimplyMarkdown."""

    def __init__(self, config: Config):
        self.config = config
        self.input_path = Path(config.input_dir)
        self.output_path = Path(config.output_dir)
        self.template_path = Path(config.template)
        self.modules: dict[str, str] = {}
        self.manifest = BuildManifest(self.output_path) if config.build.incremental else None

    def render(self) -> None:
        """Render the entire site."""
        # Copy CSS
        copy_css_file(self.config.theme, self.output_path)

        # Find and load modules
        self.modules = self._find_modules()

        # Process all files
        self._process_directory()

        # Generate sitemap
        generate_sitemap(self.output_path, self.config.root_url)

        # Generate RSS feed
        if self.config.rss.enabled:
            generate_rss_feed(
                self.output_path,
                self.config.root_url,
                self.config.rss.whitelist,
                self.config.title,
                self.config.rss.description,
            )

        # Generate search index
        generate_search_index(self.output_path, self.config.root_url)

        # Save manifest for incremental builds
        if self.manifest:
            self.manifest.save()

    def _find_modules(self) -> dict[str, str]:
        """Find and load all modules."""
        module_dict: dict[str, str] = {}
        modules_dir = self.input_path / MODULES_DIR

        if not modules_dir.exists():
            return module_dict

        for root, _, files in os.walk(modules_dir):
            for file in files:
                file_path = Path(root) / file
                filename = get_filename_without_extension(file)
                extension = get_extension(file)

                if extension == "html":
                    module_dict[filename] = read_file_content(file_path)
                else:
                    content, _ = convert_to_html(
                        read_file_content(file_path),
                        str(file_path.parent),
                    )
                    module_dict[filename] = content

        return module_dict

    def _process_directory(self) -> None:
        """Process all files in the input directory."""
        for root, dirs, files in os.walk(self.input_path):
            root_path = Path(root)

            # Create output directories
            for dir_name in dirs:
                input_dir = root_path / dir_name
                relative = input_dir.relative_to(self.input_path)
                output_dir = self.output_path / relative
                output_dir.mkdir(parents=True, exist_ok=True)

            # Process files
            for file in files:
                file_path = root_path / file
                relative_path = file_path.relative_to(self.input_path)
                output_file = self.output_path / relative_path

                # Skip modules directory
                if str(relative_path).startswith(f"{MODULES_DIR}/"):
                    continue

                # Skip files starting with underscore (drafts)
                if file.startswith("_") and not self.config.build.include_drafts:
                    continue

                # Check if rebuild needed (incremental mode)
                if self.manifest and not self.manifest.needs_rebuild(file_path):
                    continue

                if should_convert_file(file_path):
                    self._process_markdown_file(file_path, output_file, root_path)
                    if self.manifest:
                        self.manifest.update(file_path)
                else:
                    # Copy non-markdown files as-is
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, output_file)

    def _process_markdown_file(
        self,
        file_path: Path,
        output_file: Path,
        root_path: Path,
    ) -> None:
        """Process a single markdown file."""
        content = read_file_content(file_path)

        # Get initial title
        title = get_first_title(content) or extract_first_paragraph(content, character_limit=50)

        # Prepare output path
        output_file = Path(
            str(output_file.with_suffix("")).replace(", ", "-").replace(" ", "-") + ".html"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        output_file_relpath = output_file.relative_to(self.output_path)
        output_dir_relpath = output_file_relpath.parent

        # Replace module includes
        content = re.sub(
            r"\n! include (.+)",
            lambda match: self.modules.get(match.group(1).strip(), ""),
            content,
            flags=re.IGNORECASE,
        )

        # Convert to HTML
        posts_dir = str(self.input_path / "posts") if (self.input_path / "posts").exists() else None
        content, meta = convert_to_html(
            content,
            str(file_path.parent),
            posts_dir=posts_dir,
            current_file=str(file_path),
        )

        # Check if draft (via frontmatter)
        if is_draft(file_path, meta) and not self.config.build.include_drafts:
            return

        # Replace relative src links
        content = replace_relative_src_links(
            content,
            str(output_dir_relpath),
            self.config.root_url,
        )

        # Extract metadata
        meta_img = meta.get("image", [None])[0]
        meta_title = meta.get("title", [title])[0]
        meta_description = meta.get("description", [extract_first_paragraph(content)])[0]
        meta_canonical_uri = meta.get("canonical_uri", [None])[0]
        meta_date = meta.get(
            "date",
            [datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d")],
        )[0]
        meta_lang = meta.get("language", [DEFAULT_LANGUAGE])[0]
        category_tags = meta.get("tags", [])

        # Generate meta tags
        meta_tags_html = get_meta_tags(
            meta_img,
            meta_title,
            meta_description,
            meta_date,
            self.config.root_url,
            str(root_path),
            str(self.input_path),
            str(output_file_relpath),
            meta_canonical_uri,
        )

        # Build page title
        page_title = f"{meta_title} - {self.config.title}" if self.config.title else meta_title

        # Build template context
        context = {
            "lang": meta_lang,
            "root": self.config.root_url,
            "favicon_path": get_emoji_favicon_url(self.config.favicon),
            "title": page_title,
            "modules": self.modules,
            "content": content,
            "meta_tags": meta_tags_html,
            "category_tags": category_tags,
        }

        # Render template
        filled_template = fill_template({"context": context}, self.template_path)

        # Prettify HTML
        filled_template = prettify_html(filled_template)

        # Write output
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(filled_template)


def prettify_html(html: str) -> str:
    """Format HTML with proper indentation.

    Args:
        html: Raw HTML string.

    Returns:
        Prettified HTML string.
    """
    # Use lxml parser for better HTML5 support
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        # Fall back to html.parser if lxml not available
        soup = BeautifulSoup(html, "html.parser")

    # Use a formatter that doesn't add closing tags to void elements
    return soup.prettify(formatter="html5")


def render_site(config: Config) -> None:
    """Render a site using the given configuration.

    Args:
        config: Configuration object for the site.
    """
    renderer = Renderer(config)
    renderer.render()
