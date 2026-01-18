"""Search index generator for SimplyMarkdown."""


import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from bs4 import BeautifulSoup


@dataclass
class SearchDocument:
    """Represents a searchable document."""

    id: str
    url: str
    title: str
    content: str
    tags: list[str]
    date: str


def generate_search_index(
    root_directory: str | Path,
    url_root: str = "",
    output_filename: str = "search-index.json",
) -> None:
    """Generate a search index JSON file from rendered HTML files.

    This index can be used with client-side search libraries like:
    - Lunr.js
    - Pagefind
    - Fuse.js

    Args:
        root_directory: Root directory containing HTML files.
        url_root: Root URL for document links.
        output_filename: Name of the output JSON file.
    """
    root_directory = Path(root_directory)
    html_files = _get_html_files(root_directory)

    documents: list[SearchDocument] = []

    for file_path in html_files:
        doc = _extract_document(file_path, root_directory, url_root)
        if doc:
            documents.append(doc)

    # Sort by date (newest first)
    documents.sort(key=lambda d: d.date, reverse=True)

    # Write index
    output_file = root_directory / output_filename
    index_data = {
        "version": "1.0",
        "documents": [asdict(doc) for doc in documents],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)


def _get_html_files(directory: Path) -> list[Path]:
    """Get all HTML files in a directory recursively."""
    html_files: list[Path] = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".html"):
                html_files.append(Path(root) / file)
    return html_files


def _extract_document(
    file_path: Path, root_directory: Path, url_root: str
) -> SearchDocument | None:
    """Extract searchable content from an HTML file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.text if title_tag else file_path.stem

        # Extract main content
        main_tag = soup.find("main")
        if not main_tag:
            return None

        # Remove elements that shouldn't be indexed
        for element in main_tag(["script", "style", "nav", "footer", "parsers-ignore"]):
            element.decompose()

        # Get text content
        content = main_tag.get_text(separator=" ", strip=True)
        # Clean up whitespace
        content = re.sub(r"\s+", " ", content)
        # Limit content length for index size
        content = content[:2000]

        # Extract tags/categories
        tags = [tag.text.strip() for tag in soup.find_all("categorytag")]

        # Extract date
        date_meta = soup.find("meta", {"name": "pubdate"}) or soup.find(
            "meta", {"property": "og:pubdate"}
        )
        date = date_meta["content"] if date_meta else ""

        # Generate URL
        relative_path = file_path.relative_to(root_directory)
        url = f"{url_root}/{relative_path}".replace("\\", "/")
        url = url.replace("//", "/")
        url = url.replace("https:/", "https://")
        url = url.replace(".html", "")

        # Generate ID
        doc_id = str(relative_path).replace("/", "-").replace(".html", "")

        return SearchDocument(
            id=doc_id,
            url=url,
            title=title,
            content=content,
            tags=tags,
            date=date,
        )
    except Exception:
        return None
