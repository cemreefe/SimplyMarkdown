"""RSS feed generator for SimplyMarkdown."""

from __future__ import annotations

import fnmatch
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement

from bs4 import BeautifulSoup


def generate_rss_feed(
    root_directory: str | Path,
    url_root: str = "",
    uri_whitelist: str = "*",
    feed_title: str = "My RSS Feed",
    feed_description: str = "This is an RSS feed of my website.",
) -> None:
    """Generate an RSS feed from rendered HTML files.

    Args:
        root_directory: Root directory containing HTML files.
        url_root: Root URL for RSS feed links.
        uri_whitelist: Comma-separated patterns of URIs to include.
        feed_title: Title of the RSS feed.
        feed_description: Description of the RSS feed.
    """
    root_directory = Path(root_directory)
    html_files = _get_html_files(root_directory)
    whitelist_patterns = uri_whitelist.split(",")

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    title_elem = SubElement(channel, "title")
    title_elem.text = feed_title

    link_elem = SubElement(channel, "link")
    link_elem.text = url_root

    description_elem = SubElement(channel, "description")
    description_elem.text = feed_description

    feed_items: list[dict] = []

    for file_path in html_files:
        uri = str(file_path.relative_to(root_directory))
        if not _is_uri_whitelisted(uri, whitelist_patterns):
            continue

        with open(file_path, encoding="utf-8") as file:
            html_content = file.read()

        last_edit = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(
            "%a, %d %b %Y %H:%M:%S +0000"
        )
        item_title, pub_date, main_content, category_tags = _extract_metadata(
            html_content, last_edit
        )

        url = f"{url_root}/{uri}".replace("\\", "/")
        url = url.replace("//", "/")
        url = url.replace("https:/", "https://")
        url = url.replace(".html", "")

        parsed_content = _parse_main_content(main_content)

        feed_items.append(
            {
                "title": item_title,
                "link": url,
                "guid": url,
                "pubDate": pub_date,
                "description": parsed_content,
                "categories": category_tags,
            }
        )

    # Sort items by pubDate in descending order
    feed_items.sort(key=_sort_key, reverse=True)

    for item_data in feed_items:
        item = SubElement(channel, "item")

        item_title_elem = SubElement(item, "title")
        item_title_elem.text = item_data["title"]

        link_elem = SubElement(item, "link")
        link_elem.text = item_data["link"]

        guid_elem = SubElement(item, "guid")
        guid_elem.text = item_data["guid"]

        if item_data["pubDate"]:
            pub_date_elem = SubElement(item, "pubDate")
            pub_date_elem.text = item_data["pubDate"]

        description_elem = SubElement(item, "description")
        description_elem.text = item_data["description"]

        for category in item_data["categories"]:
            category_elem = SubElement(item, "category")
            category_elem.text = category

    output_file = root_directory / "rss.xml"
    ElementTree(rss).write(output_file, encoding="utf-8", xml_declaration=True)


def _get_html_files(directory: Path) -> list[Path]:
    """Get all HTML files in a directory recursively."""
    html_files: list[Path] = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".html"):
                html_files.append(Path(root) / file)
    return html_files


def _is_uri_whitelisted(uri: str, whitelist_patterns: list[str]) -> bool:
    """Check if a URI matches any whitelist pattern."""
    return any(fnmatch.fnmatch(uri, pattern.strip()) for pattern in whitelist_patterns)


def _extract_metadata(html_content: str, last_edit: str) -> tuple[str, str, str, list[str]]:
    """Extract metadata from HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")

    title = soup.find("title").text if soup.find("title") else "No title"

    pub_date_meta = soup.find("meta", {"name": "pubDate"}) or soup.find("meta", {"name": "pubdate"})
    pub_date = pub_date_meta["content"] if pub_date_meta else None
    pub_date = pub_date or last_edit

    main_content = str(soup.find("main")) if soup.find("main") else "No content"
    category_tags = [tag.text.strip() for tag in soup.find_all("categorytag")]

    return title, pub_date, main_content, category_tags


def _parse_main_content(main_content: str) -> str:
    """Clean and parse main content for RSS."""
    soup = BeautifulSoup(main_content, "html.parser")

    # Remove script, style, and other elements
    for element in soup(["script", "style", "parsers-ignore", "categorytag"]):
        element.decompose()

    # Remove all style attributes
    for tag in soup.find_all(True):
        tag.attrs = {key: value for key, value in tag.attrs.items() if key != "style"}

    # Add max-width to images
    for img in soup.find_all("img"):
        img["style"] = "max-width:100%;"

    return str(soup)


def _sort_key(item: dict) -> datetime:
    """Get sort key for RSS items by pubDate."""
    if item["pubDate"]:
        try:
            return parsedate_to_datetime(item["pubDate"])
        except (TypeError, ValueError):
            pass
    return datetime.min
