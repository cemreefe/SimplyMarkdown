from __future__ import annotations

import argparse
from pathlib import Path

from .core import BuildConfig, BuildError, SiteBuilder


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="simplymarkdown",
        description="Build a complete static site from a Markdown directory.",
    )
    command.add_argument("-i", "--input", type=Path, required=True, help="source directory")
    command.add_argument("-o", "--output", type=Path, required=True, help="destination directory")
    command.add_argument(
        "--root", required=True, help="canonical site URL, including any base path"
    )
    command.add_argument("--title", required=True, help="site title")
    command.add_argument("--css", type=Path, help="theme CSS (defaults to the bundled theme)")
    command.add_argument(
        "--template", type=Path, help="Jinja template (defaults to the bundled template)"
    )
    command.add_argument("--favicon", default="👤", help="favicon emoji")
    command.add_argument(
        "--rss-whitelist",
        default="*",
        help="comma-separated URL globs included in RSS",
    )
    command.add_argument(
        "--rss-description",
        default="This is an RSS feed of my website.",
        help="RSS channel description",
    )
    command.add_argument(
        "--preview-limit", type=int, default=6, help="blocks shown in detailed previews"
    )
    return command


def main(argv: list[str] | None = None) -> int:
    command = parser()
    args = command.parse_args(argv)
    config = BuildConfig(
        input_dir=args.input,
        output_dir=args.output,
        root_url=args.root,
        title=args.title,
        css=args.css,
        template=args.template,
        favicon=args.favicon,
        rss_whitelist=tuple(args.rss_whitelist.split(",")),
        rss_description=args.rss_description,
        preview_limit=args.preview_limit,
    )
    try:
        result = SiteBuilder(config).build()
    except BuildError as error:
        command.exit(2, f"simplymarkdown: error: {error}\n")
    print(f"Built {len(result.pages)} pages in {result.output_dir}")
    return 0
